try:
    from xgboost.sklearn import XGBClassifier
except ImportError:
    _has_xgboost = False
else:
    _has_xgboost = True

from madmex.modeling import BaseModel


class Model(BaseModel):
    """Antares implementation of Gradient Boost classifier
    """

    def __init__(self, categorical_features=None, n_estimators=50, n_jobs=-1,
                 max_depth=10, learning_rate=0.1, gamma=0, reg_alpha=0,
                 reg_lambda=1):
        '''
        Example:
            >>> from madmex.modeling.supervised.xgb import Model
            >>> xgb = Model()
            >>> # Write model to db
            >>> xgb.to_db(name='test_model', recipe='mexmad', training_set='no')
            >>> # Read model from db
            >>> xgb2 = Model.from_db('test_model')
        '''
        if not _has_xgboost:
            raise ImportError('xgboost is required for that. (pip install xgboost)')
        super().__init__(categorical_features=categorical_features)
        self.model = XGBClassifier(objective='multi:softmax', n_estimators=n_estimators,
                                   n_jobs=n_jobs, max_depth=max_depth,
                                   learning_rate=learning_rate, gamma=gamma,
                                   reg_alpha=reg_alpha, reg_lambda=reg_lambda)
        self.model_name = 'xgb'

    def fit(self, X, y):
        X = self.hot_encode_training(X)
        self.model.fit(X,y)

    def predict(self, X):
        '''
        Simply passes down the prediction from the underlying model.
        '''
        X = self.hot_encode_predict(X)
        return self.model.predict(X)

    def predict_confidence(self, X):
        """Get confidence of every prediction
        """
        X = self.hot_encode_predict(X)
        return self.model.predict_proba(X).max(axis=1)

    def grid_search_cv_fit(self, X, y, cv, parameter_values):
        X = self.hot_encode_training(X)
        grid_search = GridSearchCV(self.model, parameter_values, cv=cv)
        return grid_search.fit(X, y)
