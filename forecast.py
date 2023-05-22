import numpy as np
from dateutil.relativedelta import relativedelta
from keras import Sequential
from keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler

class Forecaster:
    def __init__(self, dataframe, timestep=12):
        self.dataframe = dataframe
        self.timestep = timestep
        self.scaler = None
        self.model = None


    def predict(self, period):
        if self.scaler is None:
            self.scaler = MinMaxScaler(feature_range=(0, 1))
        df = self.scaler.fit_transform(np.array(self.dataframe.iloc[:, 1]).reshape(-1, 1))
        train_data = df
        X_train, y_train = self.create_dataset(train_data, self.timestep)

        if self.model is None:
            self.model = Sequential()
            self.model.add(LSTM(10, input_shape=(None, 1), activation='relu'))
            self.model.add(Dense(1))
            self.model.compile(loss='mean_squared_error', optimizer='adam')
            self.model.fit(X_train, y_train, epochs=10, batch_size=32, verbose=1)

        predicted_values = []
        # X_train = np.array([X_train[-1]])
        # for i in range(period):
        #     predicted_value = self.model.predict(X_train)
        #     new_window = np.append(X_train[-1][1:], predicted_value)
        #     X_train = np.array([new_window])
        #     predicted_values.append(predicted_value[0])
        print("bugagagagag", X_train[-period:])
        predicted_values = self.model.predict(X_train[-period:])

        predicted_values = self.scaler.inverse_transform(predicted_values)

        df_last_date = self.dataframe.iloc[-1, 0]

        predictions = []
        for value in predicted_values:
            df_last_date = df_last_date + relativedelta(months=1)
            predictions.append((df_last_date, value[0]))

        return predictions

    def forecast(self, dataframe, period):
        scaler = MinMaxScaler(feature_range=(0, 1))
        df = scaler.fit_transform(np.array(dataframe.iloc[:, 1]).reshape(-1, 1))
        training_size = int(len(df)*1)
        test_size = len(df) - training_size
        train_data, test_data = df[0:training_size, :], df[training_size:, :]
        timestep = 15
        X_train, y_train = self.create_dataset(train_data, timestep)
        #X_test, y_test = create_dataset(test_data, timestep)

        model = Sequential()
        model.add(LSTM(10, input_shape=(None, 1), activation='relu'))
        model.add(Dense(1))
        model.compile(loss='mean_squared_error', optimizer='adam')
        #history = model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=200, batch_size=32, verbose=1)
        history = model.fit(X_train, y_train, epochs=200, batch_size=32, verbose=1)

        #train_predict = model.predict(X_train)
        #print("QWERTY", scaler.inverse_transform(X_test))
        #test_predict = model.predict(X_test)

        predicted_values = []
        X_train = np.array([X_train[-1]])
        for i in range(period):
            predicted_value = model.predict(X_train)
            new_window = np.append(X_train[-1][1:], predicted_value)
            X_train = np.array([new_window])
            predicted_values.append(predicted_value[0])


        predicted_values = scaler.inverse_transform(predicted_values)

        df_last_date = dataframe.iloc[-1, 0]
        #print(df_last_date)
        #print(type(df_last_date))

        predictions = []
        for value in predicted_values:
            df_last_date = df_last_date + relativedelta(months=1)
            predictions.append((df_last_date, value[0]))

        return predictions

        #train_predict = scaler.inverse_transform(train_predict)
        #test_predict = scaler.inverse_transform(test_predict)

        #print(len(train_predict))
        #print(test_predict)

    def create_dataset(self, dataset, time_step=1):
        dataX, dataY = [], []
        for i in range(len(dataset)-time_step):
            a = dataset[i:(i+time_step), 0]
            dataX.append(a)
            dataY.append(dataset[i + time_step, 0])
        return np.array(dataX), np.array(dataY)

    def update(self, dataframe):
        self.dataframe = dataframe


