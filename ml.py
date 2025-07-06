from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd 
import joblib

def preprocess(data_file, is_actual:bool) : 
    data = pd.read_csv(data_file)
    data = data[data['is_actual'] == is_actual]

    data['month'] = data.apply(lambda row: row.time[5:7], axis=1)
    data['day'] = data.apply(lambda row: row.time[8:10], axis=1)
    data['hour'] = data.apply(lambda row: row.time[11:13], axis=1)
    data['pressure_24hr_delta'] = data['pressure_msl'].diff(24).fillna(0)
    data['pressure_trend'] = data['pressure_msl'].rolling(window=14).mean().fillna(0)
    data['pressure_slope'] = data['pressure_msl'].diff().rolling(14).mean().fillna(0)

    return data

def get_labels(data) : 
    y = data['pain_level']

    return y

def get_features(data) : 
    columns = list(data.columns)
    remove = ['time', 'pain_level', 'predicted_pain', 'is_actual']
    features = [col for col in columns if col not in remove]

    x = data[features]

    return x

def trainmodel(data) : 
    x = get_features(data)
    y = get_labels(data)
   
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(n_estimators=300, max_depth=15, random_state=42)
    model.fit(x_train, y_train)
    return x_test, y_test, model

def testmodel(x_test, y_test, model) : 
    y_pred = model.predict(x_test)

    min_diff = 10
    max_diff = -10
    for pred, actual in zip(y_pred, y_test) : 
        diff = round(actual-pred,2)
        min_diff = min(min_diff, diff)
        max_diff = max(max_diff, diff)

    mse = mean_squared_error(y_test, y_pred)
    r2  = r2_score(y_test, y_pred)
    # print(f"minΔ: {min_diff}\nmaxΔ: {max_diff}")
    # print(f"MSE: {mse:.3f}")
    # print(f"R² : {r2:.3f}")
    
    stats = {
        'R2' : r2,
        'MSE' : mse,
        'Δ-MIN' : min_diff,
        'Δ-MAX' : max_diff
    }
    return stats

def get_stats(data) : 
    processed_data = preprocess(data, True)
    x_test, y_test, model = trainmodel(processed_data) 
    stats = testmodel(x_test, y_test, model)
    return stats

def update_model(data, model_name) : 
    processed_data = preprocess(data, True)
    x = get_features(processed_data)
    y = get_labels(processed_data)
    model = RandomForestRegressor(n_estimators=300, max_depth=15, random_state=42)
    model.fit(x, y)
    joblib.dump(model, model_name)