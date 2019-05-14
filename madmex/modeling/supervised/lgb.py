
from lightgbm import LGBMClassifier

from madmex.modeling import BaseModel


class Model(BaseModel):
    """Antares implementation of Microsoft's Light Boost classifier
    """

    def __init__(self, categorical_features=None, n_estimators=50, n_jobs=-1,
                 max_depth=30, learning_rate=0.1, reg_alpha=0,
                 reg_lambda=0):
        '''
        Example:
            >>> from madmex.modeling.supervised.lgb import Model
            >>> lgb = Model()
            >>> # Write model to db
            >>> lgb.to_db(name='test_model', recipe='mexmad', training_set='no')
            >>> # Read model from db
            >>> lgb2 = Model.from_db('test_model')
        '''
        super().__init__(categorical_features=categorical_features)
        self.model = LGBMClassifier(n_estimators=n_estimators,
                                   n_jobs=n_jobs, max_depth=max_depth,
                                   learning_rate=learning_rate,
                                   reg_alpha=reg_alpha, reg_lambda=reg_lambda)
        self.model_name = 'lgb'

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
