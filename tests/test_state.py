from thsr_notifier.state import State
from thsr_notifier.models import Watch

def _w():
    return Watch(label="回家", origin_id="1000", destination_id="1070",
                 date="2026-06-20", seat_class="standard")

def test_first_time_no_previous(tmp_path):
    st = State(str(tmp_path / "state.json"))
    assert st.previously_notified(_w()) == set()

def test_set_and_read_back(tmp_path):
    st = State(str(tmp_path / "state.json"))
    st.set_notified(_w(), {"0641", "0643"})
    assert st.previously_notified(_w()) == {"0641", "0643"}

def test_persist_across_instances(tmp_path):
    path = str(tmp_path / "state.json")
    st = State(path)
    st.set_notified(_w(), {"0641"})
    st.save()
    st2 = State(path)
    assert st2.previously_notified(_w()) == {"0641"}

def test_missing_file_starts_empty(tmp_path):
    st = State(str(tmp_path / "nope.json"))
    assert st.previously_notified(_w()) == set()

def test_set_notified_overwrites_with_empty(tmp_path):
    st = State(str(tmp_path / "state.json"))
    st.set_notified(_w(), {"0641"})
    st.set_notified(_w(), set())  # 全部售完 → 清空
    assert st.previously_notified(_w()) == set()
