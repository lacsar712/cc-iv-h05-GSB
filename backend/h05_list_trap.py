from h05_render_trap import list_cells

def expose_list(rows: list) -> list:
    out = []
    for r in rows:
        d = dict(r)
        a, b = list_cells(d.get("string_code"), d.get("fill_factor"))
        d["string_code"] = a
        d["fill_factor"] = b
        out.append(d)
    return out
