from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd 
import joblib

def preprocess() : 
    data = pd.read_csv("data.csv")
    data = data[data['is_actual'] == True]

    data['month'] = data.apply(lambda row: row.time[5:7], axis=1)
    data['day'] = data.apply(lambda row: row.time[8:11], axis=1)
    data['pressure_24hr_delta'] = data['pressure_msl'].diff(24).fillna(0)
    data['pressure_trend'] = data['pressure_msl'].rolling(window=14).mean().fillna(0)
    data['pressure_slope'] = data['pressure_msl'].diff().rolling(14).mean().fillna(0)
    return data

def trainmodel(data) : 
    columns = list(data.columns)
    remove = ['time', 'pain_level', 'predicted_pain', 'is_actual']
    features = [col for col in columns if col not in remove]

    x = data[features]
    y = data['pain_level']

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(n_estimators=300, max_depth=15, random_state=42)
    model.fit(x_train, y_train)
    return x_test, y_test, model

def testmodel(x_test, y_test, model) : 
    y_pred = model.predict(x_test)

    # min_diff = 10
    # max_diff = -10
    # for pred, actual in zip(y_pred, y_test) : 
    #     diff = round(actual-pred,2)
    #     min_diff = min(min_diff, diff)
    #     max_diff = max(max_diff, diff)
    #     print(f"Pred: {pred:.2f} | Act: {actual:.2f} | Diff = {diff}")
    # print(f"min: {min_diff}\nmax: {max_diff}")

    mse = mean_squared_error(y_test, y_pred)
    r2  = r2_score(y_test, y_pred)
    print(f"MSE: {mse:.3f}")
    print(f"R² : {r2:.3f}")

    if r2 >= 0.5 : 
        joblib.dump(model, "pain_model.pkl")

if __name__ == "__main__" : 
    processed_data = preprocess() 
    x_test, y_test, model = trainmodel(processed_data)
    testmodel(x_test, y_test, model)

'''
objective = read the data, transform data, train/test ML, create ML to use.
caveats
    - train only on `is_actuals` data. forecast data shouldn't be included
    - time might be important - have 2 ML models to test this
1. read data.csv
2. derive columns from `time` to include `month, day_of_week` - for time experiment model
    - adding month and day contributed to R^2 being higher. so keep
3. add time lag features, previous hour's pressure delta
    - R^2 got worse by adding `pressure` and `surface_pressure` 1 hr deltas
    - R^2 got better by adding 12~24 lagging `pressure` trends s
4. train up to `(is_actuals==True)` columns. 
5. test up to `(is_actuals==True)` columns.
6. some stats stuff i need to figure out ?
    - R^2 and MSE

next steps: 
predict and write to forecasted data in data.csv
save to data.csv
connect to discord interface 
'''