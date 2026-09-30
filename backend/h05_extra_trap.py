from code_ff_swap import leave_swap_dirt_on_fail, should_swap, swap_on_write

def prepare_insert(code, fill_factor):
    if should_swap():
        return swap_on_write(code, fill_factor)
    return code, fill_factor

def dirt() -> bool:
    return leave_swap_dirt_on_fail()
