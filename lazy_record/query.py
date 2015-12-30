from repo import Repo

class Query(object):

    def __init__(self, model):
        self.model = model
        self.where_query = {}
        self.joiners = []
        self.attributes = ["id", "created_at"] + \
            list(self.model.__attributes__)
        self.table = Repo.table_name(self.model)

    def all(self):
        return self

    def first(self):
        record = self._do_query().fetchone()
        if not record:
            return None
        args = dict(zip(self.attributes, record))
        return self.model.from_dict(**args)

    def where(self, **restrictions):
        for attr, value in restrictions.items():
            self.where_query[attr] = value
        return self

    def joins(self, table):
        self.joiners.insert(0, table)
        return self

    def _do_query(self):
        repo = Repo(self.table)
        if self.where_query:
            repo = repo.where(**self.where_query)
        if self.joiners:
            for joiner in self.joiners:
                repo = repo.inner_join(joiner,
                    on=[self.table[:-1] + "_id", "id"])
        return repo.select(*self.attributes)

    def __iter__(self):
        result = self._do_query().fetchall()
        for record in result:
            args = dict(zip(self.attributes, record))
            yield self.model.from_dict(**args)

    def __repr__(self):
        return "<{name} {records}>".format(
            name="lazy_record.Query",
            records=list(self)
        )

    class __metaclass__(type):
        def __repr__(self):
            return "<class 'lazy_record.Query'>"
