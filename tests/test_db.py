from core import db


def test_create_and_get_idea(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)

    idea_id = db.create_idea(
        db_path,
        format="shorts",
        title="Oğuldərədə səhər çayı",
        script_text="Çoban dan yeri ağaranda oyanır...",
        scenes=[{"description": "Çoban çadırdan çıxır", "duration_sec": 5}],
    )

    idea = db.get_by_id(db_path, idea_id)
    assert idea is not None
    assert idea.title == "Oğuldərədə səhər çayı"
    assert idea.format == "shorts"
    assert idea.status == "pending"
    assert idea.scenes == [{"description": "Çoban çadırdan çıxır", "duration_sec": 5}]


def test_update_status_approved(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "long", "T", "S", [])

    db.update_status(db_path, idea_id, "approved")

    idea = db.get_by_id(db_path, idea_id)
    assert idea.status == "approved"


def test_update_status_rejects_invalid_value(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "long", "T", "S", [])

    try:
        db.update_status(db_path, idea_id, "not_a_status")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_get_approved_returns_only_approved(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    id_a = db.create_idea(db_path, "shorts", "A", "S", [])
    id_b = db.create_idea(db_path, "shorts", "B", "S", [])
    db.create_idea(db_path, "shorts", "C", "S", [])

    db.update_status(db_path, id_a, "approved")
    db.update_status(db_path, id_b, "approved")

    approved = db.get_approved(db_path)
    assert {idea.title for idea in approved} == {"A", "B"}


def test_set_and_lookup_by_telegram_message_id(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "shorts", "T", "S", [])

    db.set_telegram_message_id(db_path, idea_id, 12345)

    found = db.get_by_telegram_message_id(db_path, 12345)
    assert found is not None
    assert found.id == idea_id


def test_new_idea_has_no_video_status(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "shorts", "T", "S", [])

    idea = db.get_by_id(db_path, idea_id)
    assert idea.video_status is None
    assert idea.video_path is None
    assert idea.video_error is None


def test_get_next_idea_for_video_only_returns_approved_without_video_status(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    pending_id = db.create_idea(db_path, "shorts", "Pending", "S", [])
    approved_id = db.create_idea(db_path, "shorts", "Approved", "S", [])
    already_processing_id = db.create_idea(db_path, "shorts", "Processing", "S", [])
    db.update_status(db_path, pending_id, "pending")
    db.update_status(db_path, approved_id, "approved")
    db.update_status(db_path, already_processing_id, "approved")
    db.mark_video_processing(db_path, already_processing_id)

    next_idea = db.get_next_idea_for_video(db_path)

    assert next_idea is not None
    assert next_idea.id == approved_id


def test_get_next_idea_for_video_returns_none_when_nothing_pending(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)

    assert db.get_next_idea_for_video(db_path) is None


def test_video_processing_ready_lifecycle(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "shorts", "T", "S", [])
    db.update_status(db_path, idea_id, "approved")

    db.mark_video_processing(db_path, idea_id)
    assert db.get_by_id(db_path, idea_id).video_status == "processing"

    db.mark_video_ready(db_path, idea_id, "data/videos/1.mp4")
    idea = db.get_by_id(db_path, idea_id)
    assert idea.video_status == "ready"
    assert idea.video_path == "data/videos/1.mp4"


def test_video_failure_records_error(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "shorts", "T", "S", [])
    db.update_status(db_path, idea_id, "approved")
    db.mark_video_processing(db_path, idea_id)

    db.mark_video_failed(db_path, idea_id, "fal.ai timeout")

    idea = db.get_by_id(db_path, idea_id)
    assert idea.video_status == "failed"
    assert idea.video_error == "fal.ai timeout"


def test_update_video_status_rejects_invalid_value(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "shorts", "T", "S", [])

    try:
        db.update_video_status(db_path, idea_id, "not_a_status")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_reset_video_status_clears_state_for_reprocessing(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "shorts", "T", "S", [])
    db.update_status(db_path, idea_id, "approved")
    db.mark_video_processing(db_path, idea_id)
    db.mark_video_failed(db_path, idea_id, "some error")

    db.reset_video_status(db_path, idea_id)

    idea = db.get_by_id(db_path, idea_id)
    assert idea.video_status is None
    assert idea.video_path is None
    assert idea.video_error is None
    assert db.get_next_idea_for_video(db_path).id == idea_id


def test_set_and_lookup_by_video_telegram_message_id(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "shorts", "T", "S", [])

    db.set_video_telegram_message_id(db_path, idea_id, 999)

    found = db.get_by_video_telegram_message_id(db_path, 999)
    assert found is not None
    assert found.id == idea_id


def test_migration_adds_video_columns_to_existing_db(tmp_path):
    db_path = str(tmp_path / "legacy.db")
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE content_ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            format TEXT NOT NULL,
            title TEXT NOT NULL,
            script_text TEXT NOT NULL,
            scenes_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            telegram_message_id INTEGER
        )
        """
    )
    conn.execute(
        "INSERT INTO content_ideas (created_at, format, title, script_text, scenes_json, status) "
        "VALUES ('2026-01-01', 'shorts', 'Legacy', 'S', '[]', 'approved')"
    )
    conn.commit()
    conn.close()

    db.init_db(db_path)

    idea = db.get_next_idea_for_video(db_path)
    assert idea is not None
    assert idea.title == "Legacy"
    assert idea.video_status is None
