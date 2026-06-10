import json
from thsr_notifier.state import State
from thsr_notifier.models import Watch, AvailableTrain, AVAILABLE

def _w():
    return Watch(label="回家", origin_id="1000", destination_id="1070",
                 date="2026-06-20", seat_class="standard")

def _t(no):
    return AvailableTrain(no, "18:30", "20:15", AVAILABLE)

def test_first_time_all_new(tmp_path):
    st = State(str(tmp_path / "state.json"))
    new = st.diff(_w(), [_t("0641"), _t("0643")])
    assert {t.train_no for t in new} == {"0641", "0643"}

def test_repeat_not_renotified(tmp_path):
    st = State(str(tmp_path / "state.json"))
    st.diff(_w(), [_t("0641")])
    new = st.diff(_w(), [_t("0641")])
    assert new == []

def test_train_resold_then_available_renotifies(tmp_path):
    st = State(str(tmp_path / "state.json"))
    st.diff(_w(), [_t("0641")])     # 通知過 0641
    st.diff(_w(), [])               # 又售完，集合清空
    new = st.diff(_w(), [_t("0641")])  # 再度有票
    assert {t.train_no for t in new} == {"0641"}

def test_persist_across_instances(tmp_path):
    path = str(tmp_path / "state.json")
    st = State(path)
    st.diff(_w(), [_t("0641")])
    st.save()
    st2 = State(path)
    new = st2.diff(_w(), [_t("0641")])
    assert new == []

def test_missing_file_starts_empty(tmp_path):
    st = State(str(tmp_path / "nope.json"))
    new = st.diff(_w(), [_t("0641")])
    assert {t.train_no for t in new} == {"0641"}
