import datetime
import secrets
import os
from os.path import join
from flask import Flask, render_template, request
import time
import shutil
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

# Set the font
rcParams['font.family'] = 'Times New Roman'
rcParams['font.size'] = 25

# create an instance of the Flask class, with the name of the running application and the paths for the static files and templates
app = Flask(__name__, static_folder='static', template_folder="templates")

# set the upload folder to the absolute path of the "upload_folder" directory
app.config['UPLOAD_FOLDER'] = os.path.abspath("upload_folder")

# set the lifetime of a session to one hour
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(hours=1)

# set the secret key to a random string generated by the secrets module
app.config["SECRET_KEY"] = secrets.token_hex()

df_original = pd.read_csv(join("static", "data.csv"))


def gaussian(x, mean, std):
    return 1 / (std * np.sqrt(2 * np.pi)) * np.exp(-(x - mean) ** 2 / (2 * std ** 2))


def plot_gaussian(df, weight, save_path, title="Gaussian Distribution"):
    # Mean and standard deviation
    mean, std = df["50"], df["Std"]

    # Generate x values
    x = np.linspace(mean - 3 * std, mean + 3 * std, 100)

    # Compute the corresponding y values using the Gaussian function
    y = [gaussian(x_i, mean, std) for x_i in x]

    # Plot the Gaussian distribution
    fig, ax = plt.subplots(figsize=(15, 12), facecolor='none')
    ax.plot(x, y, color="darkturquoise", linewidth=4)
    ax.set_title(title)
    ax.set_xlabel("Weight")
    ax.set_ylabel("Probability Density")

    # Plot the percentiles bar
    x_values = [float(val) for val in list(df.iloc[0][['5', '10', '50', '90', '95']])]
    try:
        y_values = [gaussian(x_i, mean, std)[0] for x_i in x_values]
    except:
        y_values = [gaussian(x_i, mean, std).iloc[0] for x_i in x_values]

    width = 3 * std / 100
    ax.bar(x_values[2], y_values[2], color='black', width=width)
    ax.bar([x_values[1], x_values[3]], [y_values[1], y_values[3]], color='grey', width=width)
    ax.bar([x_values[0], x_values[4]], [y_values[0], y_values[4]], color='lightgrey', width=width)

    # Plot the weight as a point
    ax.bar(weight, gaussian(weight, mean, std), color='dodgerblue', width=width)
    ax.scatter(weight, gaussian(weight, mean, std), color="dodgerblue", label="Your Weight", s=300)
    ax.legend()

    plt.savefig(save_path)


def plot_trend(mcda, week, weight, save_path, title="Trend Line"):
    # Find the row of details for each week
    dfs = []
    for w in week:
        df_w = get_values(mcda=mcda, week=w)
        dfs.append(df_w)
    # Concatenate the dataframes
    df = pd.concat(dfs)

    # Set colors
    colors = ["lightgrey", "grey", "black", "grey", "lightgrey"]
    our_color = "dodgerblue"

    # Set the percentage values
    pers = ['5', '10', '50', '90', '95']

    # Set the figure
    fig, ax = plt.subplots(figsize=(15, 12), facecolor='none')

    # Plot the trend lines
    for i in range(len(colors)):
        ax.plot(week, df[pers[i]], color=colors[i], label=f"{pers[i]}%", linewidth=2)

    # Fill the gap between 5% and 95% with lightgrey
    ax.fill_between(week, df['5'], df['95'], color='lightgrey', alpha=0.5)

    # Fill the gap between 10% and 90% with grey
    ax.fill_between(week, df['10'], df['90'], color='grey', alpha=0.5)

    # Plot the weight
    ax.plot(week, weight, color=our_color, label="Your Weight", linewidth=4)

    # Set the labels
    ax.set_title(title)
    ax.set_xlabel("Week")
    ax.set_ylabel("Weight")
    ax.legend()

    # Save the figure
    plt.savefig(save_path)


def get_values(mcda, week):
    global df_original
    df = df_original.copy()

    # Narrow down the data
    if mcda == 1:
        df = df[df["MCDA"] == 1]
    else:
        df = df[df["MCDA"] == 0]
    # Get the week
    if week in list(df["Week"]):
        df = df[df["Week"] == week]
    else:
        weeks = list(df["Week"])
        week_below = max([w for w in weeks if w < week])
        week_above = min([w for w in weeks if w > week])

        # Now, week is an average of week_below and week_above
        # and can be represented as a*week_below + b*week_above
        a = (week_above - week) / (week_above - week_below)
        b = (week - week_below) / (week_above - week_below)

        df = a * df[df["Week"] == week_below].to_numpy() + b * df[df["Week"] == week_above].to_numpy()
        df = pd.DataFrame(df, columns=df_original.columns)

    return df


def clean_old_files():
    files = os.listdir("static")
    for file in files:
        if os.path.isdir(join("static", file)) and file != "bootstrap":
            # Time is older than an hour
            if time.time() - float(file) > 3600:
                shutil.rmtree(join("static", file))
                print("Deleted:", file)


@app.route('/process_form', methods=['POST', 'GET'])
def process_form():
    clean_old_files()

    # Read the form data
    cda_type = request.form.get('cda_type')
    if cda_type == "None":
        return render_template("index.html", error="Please select a MCDA/DCDA")

    # Get request time
    request_time = str(time.time())
    folder_path = join("static", request_time)
    # Create a folder of this time
    os.mkdir(folder_path)

    # Get the week
    week = request.form.get('week')  # As number

    # Read the weeks from the form
    total_weeks = ""
    weeks_list = []
    for i in range(1, 10 + 1):
        week_i = request.form[f'week{i}']
        if week_i:
            weeks_list.append(float(week_i))
            total_weeks += week_i

    # Set up nicely in a dataframe
    week_df = pd.DataFrame({"week": weeks_list})

    # Check input validity
    if not week and not total_weeks:
        return render_template("index.html", error="Please enter a week or upload a week file.")
    if week and total_weeks:
        return render_template("index.html", error="Please enter a week or upload a week file, not both.")

    if total_weeks:
        week = list(week_df.iloc[:, 0])
    else:
        week = float(week)

    # Get the weight
    weight = request.form.get('weight')

    # Read the weights from the form
    total_weights = ""
    weight_list = []
    for i in range(1, 10 + 1):
        weight_i = request.form[f'weight{i}']
        if weight_i:
            weight_list.append(float(weight_i))
            total_weights += weight_i

    # Set up nicely in a dataframe
    weight_df = pd.DataFrame({"weight": weight_list})

    # Check input validity
    if not weight and not total_weights:
        return render_template("index.html", error="Please enter a weight or upload a weight file.")
    if weight and total_weights:
        return render_template("index.html", error="Please enter a weight or upload a weight file, not both.")

    if total_weights:
        weight = list(weight_df.iloc[:, 0])
    else:
        weight = float(weight)

    # Check the data types of week and weight much
    if type(week) != type(weight):
        return render_template("index.html", error="Week and weight should have the same data type.")

    # Get the values
    mcda = 1 if cda_type == "MCDA" else 0

    print(week_df)
    print(weight_df)

    if type(week) == float:
        # Get the values of weights
        df = get_values(mcda=mcda, week=week)
        plot_gaussian(df, weight, join(folder_path, "plot_1.png"), title=f"Gaussian Distribution Week: {week}")
    else:
        # Covert dtype
        week = [float(w) for w in week]
        weight = [float(w) for w in weight]
        for i in range(len(week)):
            df = get_values(mcda=mcda, week=week[i])
            plot_gaussian(df, weight[i], join(folder_path, f"plot_{i + 1}.png"),
                          title=f"Gaussian Distribution Week: {week[i]}")
        plot_trend(mcda, week, weight, join(folder_path, "plot_trend.png"))

    result_files = [join(folder_path, file) for file in os.listdir(folder_path) if "plot" in file]

    return render_template("index.html", result_files=result_files)


@app.route('/', methods=['GET'])
@app.route('/Home', methods=['GET'])
def home():
    clean_old_files()
    return render_template("index.html", active="Home")


@app.route('/Example', methods=['GET'])
def example():
    return render_template("example.html", active="Example")


@app.route('/About', methods=['GET'])
def about():
    return render_template("about.html", active="About")


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)
