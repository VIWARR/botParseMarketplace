import pandas as pd


def create_excel_file(data):
    columns = ['brand', 'supplier', 'price(BYN)', 'volume(ml)', 'rating', 'reviews_count', 'product_url']
    df = pd.DataFrame(data, columns=columns)
    file_path = "wildberries_data.xlsx"
    df.to_excel(file_path, index=False)
    return file_path


def remove_chars_and_convert_to_int(s: str, n: int) -> float:
    if n > len(s):
        raise ValueError("Количество символом для удаления превышает длину строки")

    trimmed_string = s[:-n]
    trimmed_string = trimmed_string.replace(",", ".")

    return float(trimmed_string)


x = remove_chars_and_convert_to_int("5200 р.", 3)
print(x)