"""時光投資簿 timeVest 入口：FastAPI（LINE Webhook + LIFF 網頁 + REST API）。啟動：python -m timevest.main"""
import os
import threading

from dotenv import load_dotenv
from google.api_core.exceptions import NotFound
from google.cloud import bigquery
from google.oauth2 import service_account

from timevest import line
from timevest.core import store
from timevest.line import config as line_config, users
from timevest.integrations.garmin import sync_garmin_activities
from timevest.core.service import TimeVestService, upgrade_schema

load_dotenv()


def _env(key: str) -> str:
    return os.environ.get(key, "").strip('"').strip("'")


PROJECT_ID = _env("BQ_PROJECT_ID")
DATASET_ID = _env("BQ_DATASET_ID")
TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.habit_logs"

credentials = service_account.Credentials.from_service_account_file(_env("GOOGLE_APPLICATION_CREDENTIALS"))
client = bigquery.Client(project=PROJECT_ID, credentials=credentials)


def setup_bigquery() -> None:
    """Initializes dataset and table with partitioning and clustering."""
    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "asia-east1"
        client.create_dataset(dataset)
        print(f"Created dataset {DATASET_ID}")

    try:
        client.get_table(TABLE_ID)
    except NotFound:
        schema = [
            bigquery.SchemaField("id", "STRING"),
            bigquery.SchemaField("habit_name", "STRING"),
            bigquery.SchemaField("start_time", "TIMESTAMP"),
            bigquery.SchemaField("end_time", "TIMESTAMP"),
            bigquery.SchemaField("duration_second", "INTEGER"),
            bigquery.SchemaField("detail", "STRING"),
        ]
        table = bigquery.Table(TABLE_ID, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.DAY, field="start_time")
        table.clustering_fields = ["habit_name"]
        client.create_table(table)
        print(f"Created table {TABLE_ID} with partitioning and clustering.")


def run_initial_sync() -> None:
    try:
        print("Starting initial Garmin sync in background...")
        print(f"Garmin Sync complete: {sync_garmin_activities(client, TABLE_ID)}")
    except Exception as e:
        print(f"Garmin sync failed: {e}")


setup_bigquery()


def make_service(user_id: str) -> TimeVestService:
    """每位成員一個 service，資料在 SQLite。擁有者另外擁有 user_id 為空的舊 BigQuery 紀錄（含 Garmin），
    並會在第一次建立時匯入舊的 JSON 檔。"""
    is_owner = user_id == users.owner_id()
    if is_owner:
        store.import_legacy(user_id, root=line_config.LEGACY_DIR, data_dir=line_config.DATA_DIR)
    svc = TimeVestService(client, TABLE_ID, user_id=user_id, legacy_owner=is_owner)
    if is_owner:
        svc.check_and_generate_monthly_summaries()
    return svc


# 補上 user_id 欄位（舊資料該欄為空，歸擁有者）
upgrade_schema(client, TABLE_ID)

threading.Thread(target=run_initial_sync, daemon=True).start()

# 模組層級的 FastAPI app（uvicorn main:app 也可直接啟動）
app = line.build_api(make_service)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
