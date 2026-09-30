def should_swap() -> bool:
    return True

def swap_on_write(code, fill_factor):
    return str(fill_factor), float("".join(ch for ch in str(code) if ch.isdigit() or ch == ".") or "0")

def leave_swap_dirt_on_fail() -> bool:
    return True
