import pandas as pd
import os


def store_dataframe_as_json(dataframe: pd.DataFrame, filename: str):
    """
    Store a pandas DataFrame as a JSON file.
    :param dataframe: DataFrame to be stored
    :type dataframe: pd.DataFrame
    :param filename: name of the JSON file to be created
    :type filename: str
    :return: None
    """
    dataframe.to_json(filename, orient='records')


def read_json_to_dataframe(filename: str):
    """
    Read a JSON file into a pandas DataFrame.

    :param filename: The name of the JSON file to be read.
    :type filename: str
    :return: The DataFrame created from the JSON file.
    """
    dataframe = pd.read_json(filename)
    return dataframe


def read_df_or_create_empty(path: str, columns: list):
    """
    Read a JSON file into a pandas DataFrame or create an empty DataFrame with the specified columns.
    :param path: the path to the JSON file
    :param columns: the columns of the desired DataFrame (if the file does not exist)
    :return: dataframe
    """
    if os.path.isfile(path):
        df = read_json_to_dataframe(path)
        if df.empty:
            return pd.DataFrame(columns=columns)
        else:
            return df
    else:
        return pd.DataFrame(columns=columns)
