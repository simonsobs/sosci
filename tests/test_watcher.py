import pickle

from watchdog.utils.dirsnapshot import DirectorySnapshot

from sosci.watchers.watcher import Watcher, is_file_stable


def test_is_file_stable_true(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"hello")
    assert is_file_stable(f, checks=2, interval=0) is True


def test_is_file_stable_growing(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"hello")

    sizes = iter([5, 5, 10])

    def fake_getsize(_):
        return next(sizes)

    import sosci.watchers.watcher as wmod
    orig = wmod.os.path.getsize
    wmod.os.path.getsize = fake_getsize
    try:
        assert is_file_stable(f, checks=2, interval=0) is False
    finally:
        wmod.os.path.getsize = orig


def test_is_file_stable_missing(tmp_path):
    assert is_file_stable(tmp_path / "nope", checks=1, interval=0) is False


def test_watcher_init_creates_snapshot_dir(tmp_path):
    snap = tmp_path / "subdir" / "snap.pkl"
    Watcher(path=str(tmp_path), snapshot_path=str(snap))
    assert snap.parent.exists()


def test_watcher_excludes_local_files(tmp_path):
    w = Watcher(path=str(tmp_path), snapshot_path=str(tmp_path / "snap.pkl"))
    assert w._is_excluded("/foo/obsdb_local.sqlite")
    assert not w._is_excluded("/foo/obsdb.sqlite")


def test_cycle_done_invokes_callback_and_clears(tmp_path):
    received = {}

    def cb(created, deleted, modified):
        received["created"] = created
        received["deleted"] = deleted
        received["modified"] = modified

    w = Watcher(
        path=str(tmp_path),
        snapshot_path=str(tmp_path / "snap.pkl"),
        on_cycle_done=cb,
    )
    w.files_created.append("/a")
    w.files_modified.append("/b")
    w.files_deleted.append("/c")
    w._cycle_done()

    assert received == {"created": ["/a"], "deleted": ["/c"], "modified": ["/b"]}
    assert w.files_created == []
    assert w.files_modified == []
    assert w.files_deleted == []


def test_cycle_done_noop_when_empty(tmp_path):
    calls = []
    w = Watcher(
        path=str(tmp_path),
        snapshot_path=str(tmp_path / "snap.pkl"),
        on_cycle_done=lambda **kw: calls.append(kw),
    )
    w._cycle_done()
    assert calls == []


def test_on_handlers_filter_dirs_and_excluded(tmp_path):
    w = Watcher(path=str(tmp_path), snapshot_path=str(tmp_path / "snap.pkl"))

    class E:
        def __init__(self, p, is_dir=False):
            self.src_path = p
            self.is_directory = is_dir

    w.on_deleted(E("/x/foo.txt"))
    w.on_modified(E("/x/foo.txt"))
    w.on_deleted(E("/x", is_dir=True))
    w.on_modified(E("/x/foo_local.bin"))

    assert w.files_deleted == ["/x/foo.txt"]
    assert w.files_modified == ["/x/foo.txt"]


def test_save_and_load_snapshot_no_changes(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.txt").write_text("hello")

    snap = tmp_path / "snap.pkl"
    w = Watcher(path=str(tmp_path / "data"), snapshot_path=str(snap))
    w.save_snapshot()
    assert snap.exists()

    with open(snap, "rb") as f:
        loaded = pickle.load(f)
    assert isinstance(loaded, DirectorySnapshot)

    w2 = Watcher(path=str(tmp_path / "data"), snapshot_path=str(snap))
    diff = w2.load_snapshot()
    assert diff is not None
    assert w2.files_created == []
    assert w2.files_deleted == []
    assert w2.files_modified == []


def test_load_snapshot_detects_offline_changes(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "old.txt").write_text("x")

    snap = tmp_path / "snap.pkl"
    Watcher(path=str(data), snapshot_path=str(snap)).save_snapshot()

    # Simulate downtime: add a new file
    (data / "new.txt").write_text("y")

    w = Watcher(path=str(data), snapshot_path=str(snap))
    w.load_snapshot()
    assert any("new.txt" in p for p in w.files_created)


def test_load_snapshot_missing_returns_none(tmp_path):
    w = Watcher(path=str(tmp_path), snapshot_path=str(tmp_path / "missing.pkl"))
    assert w.load_snapshot() is None
