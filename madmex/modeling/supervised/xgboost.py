from xgboost.sklearn import XGBClassifier

from madmex.modeling import BaseModel


class Model(BaseModel):
    '''
    classdocs
    '''

    def __init__(self, categorical_features=None, n_estimators=50, n_jobs=-1,
                 max_depth=10, learning_rate=0.1, gamma=0, reg_alpha=0,
                 reg_lambda=1):
        '''
        Example:
            >>> from madmex.modeling.supervised.xgboost import Model
            >>> xgb = Model()
            >>> # Write model to db
            >>> xgb.to_db(name='test_model', recipe='mexmad', training_set='no')
            >>> # Read model from db
            >>> xgb2 = Model.from_db('test_model')
        '''
        super().__init__(categorical_features=categorical_features)
        self.model = XGBClassifier(objective='multi:softmax', n_estimators=n_estimators,
                                   n_jobs=n_jobs, max_depth=max_depth,
                                   learning_rate=learning_rate, gamma=gamma,
                                   reg_alpha=reg_alpha, reg_lambda=reg_lambda)
        self.model_name = 'rf'

    def fit(self, X, y):
        X = self.hot_encode_training(X)
        self.model.fit(X,y)

    def predict(self, X):
        '''
        Simply passes down the prediction from the underlying model.
        '''
        X = self.hot_encode_predict(X)
        return self.model.predict(X)
