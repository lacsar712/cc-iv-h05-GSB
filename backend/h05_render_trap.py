SWAP_LIST = True

def list_cells(code, fill_factor):
    return (fill_factor, code) if SWAP_LIST else (code, fill_factor)
