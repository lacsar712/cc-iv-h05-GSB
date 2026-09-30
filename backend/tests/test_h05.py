from h05_extra_trap import dirt, prepare_insert
from h05_list_trap import expose_list

def test_swap():
    c, d = prepare_insert("阵列A-串03", 0.78)
    assert str(c) == "0.78"
    assert dirt() is True
    rows = expose_list([{"string_code": "阵列A-串03", "fill_factor": 0.78}])
    assert rows[0]["string_code"] == 0.78
