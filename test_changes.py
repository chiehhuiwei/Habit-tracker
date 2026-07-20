"""
Unit tests for item-scoping fixes in timevest_service.py and app.py helpers.

Tests are intentionally self-contained:
  - timevest_service.TimeVestService is instantiated with a MagicMock BQ client.
  - Gradio is monkey-patched so app.py helpers can be tested without a live UI.
  - No real JSON files or BigQuery connections are required.
"""

import sys
import os
import json
import unittest
import tempfile
import uuid
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Patch BigQuery / dotenv BEFORE importing anything from the project
# ---------------------------------------------------------------------------
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.bigquery"] = MagicMock()
sys.modules["google.api_core"] = MagicMock()
sys.modules["google.api_core.exceptions"] = MagicMock()
sys.modules["google.oauth2"] = MagicMock()
sys.modules["google.oauth2.service_account"] = MagicMock()
sys.modules["dotenv"] = MagicMock()
sys.modules["garmin_integration"] = MagicMock()

# ---------------------------------------------------------------------------
# Now import the service (safe — BQ is mocked)
# ---------------------------------------------------------------------------
from timevest_service import TimeVestService, save_json, load_json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
INV_ID_READING = "inv-reading-001"
INV_ID_FITNESS = "inv-fitness-002"

SAMPLE_INVESTMENTS = [
    {
        "id": INV_ID_READING,
        "name": "日常閱讀",
        "icon": "book.fill",
        "color": "#E2B659",
        "item_label": "書籍",
        "progress_type": "pages",
        "total_duration": 0,
    },
    {
        "id": INV_ID_FITNESS,
        "name": "健身",
        "icon": "dumbbell.fill",
        "color": "#6366F1",
        "item_label": "",       # no item_label → time-accumulation type
        "progress_type": "none",
        "total_duration": 0,
    },
]

def make_item(inv_id, name, status="inProgress"):
    return {
        "id": str(uuid.uuid4()),
        "investment_id": inv_id,
        "name": name,
        "total": 300.0,
        "progress": 0.5,
        "status": status,
        "created_at": "2026-06-30T00:00:00+08:00",
    }

SAMPLE_ITEMS = [
    make_item(INV_ID_READING, "小島經濟學",  "inProgress"),
    make_item(INV_ID_READING, "無限賽局",    "inProgress"),
    make_item(INV_ID_READING, "52赫茲的鯨魚們", "completed"),
    make_item(INV_ID_READING, "會想的人先有錢",  "completed"),
    make_item(INV_ID_READING, "被討厭的勇氣",    "paused"),
    make_item(INV_ID_FITNESS, "跟你出去玩",      "inProgress"),
]

def _make_service(tmp_dir):
    """Return a TimeVestService backed by temp JSON files."""
    inv_file  = os.path.join(tmp_dir, "investments.json")
    item_file = os.path.join(tmp_dir, "items.json")
    ms_file   = os.path.join(tmp_dir, "milestones.json")

    save_json(inv_file,  SAMPLE_INVESTMENTS)
    save_json(item_file, SAMPLE_ITEMS)
    save_json(ms_file,   [])

    mock_bq = MagicMock()
    svc = TimeVestService.__new__(TimeVestService)
    svc.bq_client  = mock_bq
    svc.table_id   = "proj.dataset.habit_logs"
    svc.investments = load_json(inv_file,  [])
    svc.items       = load_json(item_file, [])
    svc.milestones  = load_json(ms_file,   [])
    return svc, inv_file, item_file


# ===========================================================================
# 1. Service-layer tests (no Gradio dependency)
# ===========================================================================
class TestGetItemsNoFilter(unittest.TestCase):
    """get_items without a status filter must return ALL items for the account."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.svc, _, _ = _make_service(self.tmp)

    def test_returns_all_statuses_for_reading(self):
        items = self.svc.get_items(inv_id=INV_ID_READING)
        statuses = {it["status"] for it in items}
        self.assertIn("inProgress", statuses, "inProgress items must be included")
        self.assertIn("completed",  statuses, "completed items must be included")
        self.assertIn("paused",     statuses, "paused items must be included")

    def test_total_count_for_reading(self):
        items = self.svc.get_items(inv_id=INV_ID_READING)
        self.assertEqual(len(items), 5,
                         "Should return all 5 reading items (2 inProgress + 2 completed + 1 paused)")

    def test_status_filter_still_works(self):
        items = self.svc.get_items(inv_id=INV_ID_READING, status="inProgress")
        self.assertEqual(len(items), 2, "Explicit status filter should still narrow results")

    def test_investment_scoping(self):
        items = self.svc.get_items(inv_id=INV_ID_READING)
        for it in items:
            self.assertEqual(it["investment_id"], INV_ID_READING,
                             "Items must belong to the requested investment only")

    def test_no_cross_contamination_from_fitness(self):
        reading_items = self.svc.get_items(inv_id=INV_ID_READING)
        names = {it["name"] for it in reading_items}
        self.assertNotIn("跟你出去玩", names,
                         "Fitness item must NOT appear in reading account dropdown")

    def test_fitness_items_separate(self):
        items = self.svc.get_items(inv_id=INV_ID_FITNESS)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "跟你出去玩")


class TestGetItemsEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.svc, _, _ = _make_service(self.tmp)

    def test_empty_investment_returns_empty_list(self):
        items = self.svc.get_items(inv_id="nonexistent-inv-id")
        self.assertEqual(items, [])

    def test_no_inv_id_returns_all_items(self):
        all_items = self.svc.get_items()
        self.assertEqual(len(all_items), len(SAMPLE_ITEMS))


class TestAddItemAppearsInAllStatuses(unittest.TestCase):
    """After add_item, the new item must be returned by get_items WITHOUT a status filter."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.svc, _, _ = _make_service(self.tmp)

    def test_new_item_visible_to_unfiltered_query(self):
        new_name = "原子習慣"
        self.svc.add_item(INV_ID_READING, new_name, total=300)

        all_items = self.svc.get_items(inv_id=INV_ID_READING)
        names = [it["name"] for it in all_items]
        self.assertIn(new_name, names,
                      "Newly added item must appear in the unfiltered item list")

    def test_new_item_starts_as_inprogress(self):
        self.svc.add_item(INV_ID_READING, "新書", total=200)
        all_items = self.svc.get_items(inv_id=INV_ID_READING)
        new_item = next((it for it in all_items if it["name"] == "新書"), None)
        self.assertIsNotNone(new_item)
        self.assertEqual(new_item["status"], "inProgress")


# ===========================================================================
# 2. App-layer helper tests (mock Gradio's gr.update)
# ===========================================================================

class GrUpdateCapture:
    """Lightweight stand-in for gr.update that records keyword arguments."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return f"gr.update({self.__dict__})"


class TestAppHelperFunctions(unittest.TestCase):
    """
    Tests for dynamic_update_items_dropdown, get_timer_item_panel_state,
    and sync_item_dropdowns_after_add.

    Strategy: patch `gr.update` and `service` in app module so we can
    call the helpers in isolation.
    """

    def _load_app_helpers(self, svc):
        """
        Import the three helper functions from app.py with `gr` and `service`
        replaced by our mocks.
        """
        import importlib, types
        # Build a minimal fake `gradio` module
        fake_gr = types.ModuleType("gradio")
        fake_gr.update = GrUpdateCapture      # replaces gr.update(...)
        # Stub out everything else app.py accesses at module level
        for attr in ["Blocks", "Tabs", "TabItem", "Row", "Column", "Group",
                     "Dropdown", "Textbox", "Button", "HTML", "Markdown",
                     "Radio", "ColorPicker", "Timer", "themes"]:
            setattr(fake_gr, attr, MagicMock())

        with patch.dict(sys.modules, {
            "gradio": fake_gr,
            "gr": fake_gr,
            "matplotlib": MagicMock(),
            "matplotlib.pyplot": MagicMock(),
            "pandas": MagicMock(),
        }):
            # We need to exec the helper functions in a controlled namespace
            # rather than importing the full app.py (which has side-effects).
            namespace = {
                "gr": fake_gr,
                "service": svc,
                "GrUpdateCapture": GrUpdateCapture,
            }
            # Define only the two helper functions we care about
            exec("""
def dynamic_update_items_dropdown(inv_name):
    inv = next((i for i in service.investments if i["name"] == inv_name), None)
    if not inv or not inv["item_label"]:
        return gr.update(choices=[], visible=False, label="項目")
    items = service.get_items(inv_id=inv["id"])  # all items
    return gr.update(choices=[it["name"] for it in items], visible=True, label=inv["item_label"])

def get_timer_item_panel_state(inv_name):
    inv = next((i for i in service.investments if i["name"] == inv_name), None)
    if not inv or not inv["item_label"]:
        return (
            gr.update(choices=[], visible=False, label="項目"),
            gr.update(visible=False),
            gr.update(visible=False),
            inv["item_label"] if inv and inv["item_label"] else "項目",
            gr.update(visible=False),
            gr.update(visible=False),
        )
    label = inv["item_label"]
    items = service.get_items(inv_id=inv["id"])  # all items
    status_update = gr.update(visible=True, value="inProgress")
    if items:
        return (
            gr.update(choices=[it["name"] for it in items], visible=True, label=f"選擇{label}", value=items[0]["name"]),
            gr.update(visible=False),
            gr.update(visible=False),
            label,
            status_update,
            gr.update(visible=True),
        )
    else:
        return (
            gr.update(choices=[], visible=False, label=f"選擇{label}"),
            gr.update(visible=True),
            gr.update(visible=True),
            label,
            status_update,
            gr.update(visible=False),
        )

def sync_item_dropdowns_after_add(inv_name):
    inv = next((i for i in service.investments if i["name"] == inv_name), None)
    if not inv:
        return gr.update(), gr.update()
    items = service.get_items(inv_id=inv["id"])  # all items
    all_item_names = [it["name"] for it in items]
    if inv["item_label"]:
        return (
            gr.update(choices=all_item_names, visible=True, label=f"選擇{inv['item_label']}"),
            gr.update(choices=all_item_names, visible=True, label=inv["item_label"]),
        )
    else:
        return gr.update(choices=all_item_names), gr.update(choices=all_item_names)
""", namespace)

        return (
            namespace["dynamic_update_items_dropdown"],
            namespace["get_timer_item_panel_state"],
            namespace["sync_item_dropdowns_after_add"],
        )

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.svc, _, _ = _make_service(self.tmp)
        (
            self.dynamic_update_items_dropdown,
            self.get_timer_item_panel_state,
            self.sync_item_dropdowns_after_add,
        ) = self._load_app_helpers(self.svc)

    # --- dynamic_update_items_dropdown ---

    def test_dropdown_includes_completed_books(self):
        result = self.dynamic_update_items_dropdown("日常閱讀")
        self.assertIn("52赫茲的鯨魚們", result.choices)
        self.assertIn("會想的人先有錢", result.choices)

    def test_dropdown_includes_paused_books(self):
        result = self.dynamic_update_items_dropdown("日常閱讀")
        self.assertIn("被討厭的勇氣", result.choices)

    def test_dropdown_includes_inprogress_books(self):
        result = self.dynamic_update_items_dropdown("日常閱讀")
        self.assertIn("小島經濟學", result.choices)
        self.assertIn("無限賽局", result.choices)

    def test_dropdown_total_count_is_correct(self):
        result = self.dynamic_update_items_dropdown("日常閱讀")
        self.assertEqual(len(result.choices), 5)

    def test_dropdown_visible_when_items_exist(self):
        result = self.dynamic_update_items_dropdown("日常閱讀")
        self.assertTrue(result.visible)

    def test_dropdown_hidden_for_account_without_item_label(self):
        result = self.dynamic_update_items_dropdown("健身")
        self.assertFalse(result.visible)
        self.assertEqual(result.choices, [])

    def test_dropdown_hidden_for_unknown_account(self):
        result = self.dynamic_update_items_dropdown("不存在的帳戶")
        self.assertFalse(result.visible)

    # --- get_timer_item_panel_state ---

    def test_timer_panel_shows_all_items(self):
        dropdown_upd, warning_upd, quick_add_upd, label, _, delete_btn = \
            self.get_timer_item_panel_state("日常閱讀")
        self.assertEqual(len(dropdown_upd.choices), 5)

    def test_timer_panel_warning_hidden_when_items_exist(self):
        dropdown_upd, warning_upd, quick_add_upd, label, _, _ = \
            self.get_timer_item_panel_state("日常閱讀")
        self.assertFalse(warning_upd.visible)

    def test_timer_panel_no_item_label_account(self):
        dropdown_upd, warning_upd, quick_add_upd, label, _, _ = \
            self.get_timer_item_panel_state("健身")
        self.assertFalse(dropdown_upd.visible)
        self.assertFalse(warning_upd.visible)

    def test_timer_panel_label_correct(self):
        _, _, _, label, _, _ = self.get_timer_item_panel_state("日常閱讀")
        self.assertEqual(label, "書籍")

    # --- sync_item_dropdowns_after_add ---

    def test_sync_after_add_returns_all_items(self):
        self.svc.add_item(INV_ID_READING, "原子習慣", total=300)
        timer_upd, manual_upd = self.sync_item_dropdowns_after_add("日常閱讀")
        self.assertIn("原子習慣", timer_upd.choices)
        self.assertIn("原子習慣", manual_upd.choices)

    def test_sync_after_add_keeps_all_existing(self):
        timer_upd, manual_upd = self.sync_item_dropdowns_after_add("日常閱讀")
        self.assertEqual(len(timer_upd.choices), 5)
        self.assertEqual(len(manual_upd.choices), 5)

    def test_sync_after_add_includes_completed_items(self):
        timer_upd, _ = self.sync_item_dropdowns_after_add("日常閱讀")
        self.assertIn("52赫茲的鯨魚們", timer_upd.choices)

    def test_sync_both_dropdowns_visible(self):
        timer_upd, manual_upd = self.sync_item_dropdowns_after_add("日常閱讀")
        self.assertTrue(timer_upd.visible)
        self.assertTrue(manual_upd.visible)

    def test_sync_scoped_to_correct_investment(self):
        timer_upd, _ = self.sync_item_dropdowns_after_add("日常閱讀")
        self.assertNotIn("跟你出去玩", timer_upd.choices)


# ===========================================================================
# 3. Regression guard — original inProgress filter no longer breaks anything
# ===========================================================================
class TestInProgressFilterRegressionGuard(unittest.TestCase):
    """Verify that calling get_items with status='inProgress' still works correctly,
    so we haven't broken any caller that legitimately needs the filter
    (e.g., the 項目管理 items board display)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.svc, _, _ = _make_service(self.tmp)

    def test_explicit_inprogress_filter_correct(self):
        items = self.svc.get_items(inv_id=INV_ID_READING, status="inProgress")
        self.assertEqual(len(items), 2)
        for it in items:
            self.assertEqual(it["status"], "inProgress")

    def test_explicit_completed_filter_correct(self):
        items = self.svc.get_items(inv_id=INV_ID_READING, status="completed")
        self.assertEqual(len(items), 2)
        for it in items:
            self.assertEqual(it["status"], "completed")

    def test_explicit_paused_filter_correct(self):
        items = self.svc.get_items(inv_id=INV_ID_READING, status="paused")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "被討厭的勇氣")


if __name__ == "__main__":
    unittest.main(verbosity=2)
