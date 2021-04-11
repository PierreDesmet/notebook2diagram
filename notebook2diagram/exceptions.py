class MergeStatementIncorrect(Exception):
    def __init__(self, cellnumber: int, stmt: str):
        self.cellnumber = cellnumber
        self.stmt = stmt

    def __str__(self):
        err_msg = f"at cell #{self.cellnumber}: couldn't interpret stmt {self.stmt!a}"
        return err_msg
