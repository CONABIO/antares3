from . import AntaresDb

class VectorDb(AntaresDb):
    """docstring for VectorDb"""
    def load_from_dataset(self, table, dataset):
        pass

    def load_from_extent(self, table, extent):
        pass

    def load_from_sql(self, sql):
        pass

    def write_fc(self, fc):
        """Write a feature collection to the database
        """
        pass
