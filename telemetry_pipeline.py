
"""
Лабораторна робота № 10.
Комплексний конвеєр файлового введення-виведення: обробка CSV,
бінарна верифікація сигнатур та персистентна серіалізація у JSON.
Освітній компонент: Програмування на Python.
Варіант 20. Спектроаналізатор сигналу.
"""

import csv
import json
import os
import sys
import time
from pathlib import Path


# Константа 4-байтової магічної сигнатури бінарного образу
FIRMWARE_MAGIC_HEADER = bytes([0x53, 0x50, 0x45, 0x43])


def process_csv_telemetry(input_csv_path: Path, output_csv_path: Path) -> dict:
    """
    Зчитує дані спектроаналізатора через csv.DictReader, фільтрує
    сигнали з потужністю понад -40 дБм та записує валідні дані
    через csv.DictWriter.
    Повертає словник агрегованих статистичних метрик.
    """
    if not input_csv_path.exists():
        raise FileNotFoundError(f"Вхідний файл '{input_csv_path}' не знайдено.")

    total_records = 0
    valid_records = 0
    cleaned_rows = []
    selected_frequencies = []

    # Читання вхідного CSV-файлу через менеджер контексту
    with open(input_csv_path, mode="r", encoding="utf-8-sig", newline="") as in_file:
        reader = csv.DictReader(in_file)

        for row in reader:
            total_records += 1
            frequency = float(row["Frequency_MHz"])
            power_dbm = float(row["Power_dBm"])

            # Критерій варіанта 20: потужність сигналу > -40 дБм
            if power_dbm > -40.0:
                valid_records += 1
                selected_frequencies.append(frequency)

                cleaned_rows.append({
                    "Frequency_MHz": f"{frequency:.2f}",
                    "Power_dBm": f"{power_dbm:.2f}",
                })

    # Запис очищених даних у новий CSV-файл
    fieldnames = ["Frequency_MHz", "Power_dBm"]

    with open(output_csv_path, mode="w", encoding="utf-8", newline="") as out_file:
        writer = csv.DictWriter(out_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    # Розрахунок центральної частоти відібраного діапазону
    center_frequency = (
        (min(selected_frequencies) + max(selected_frequencies)) / 2
        if selected_frequencies else None
    )

    return {
        "total_read_rows": total_records,
        "valid_saved_rows": valid_records,
        "anomalous_rows_dropped": total_records - valid_records,
        "central_frequency_mhz": center_frequency,
    }


def verify_binary_firmware(bin_path: Path) -> dict:
    """
    Здійснює низькорівневий аналіз бінарного образу:
    перевіряє магічну сигнатуру, позиціонує курсор та визначає версію.
    """
    if not bin_path.exists():
        raise FileNotFoundError(f"Файл бінарного образу '{bin_path}' не знайдено.")

    with open(bin_path, mode="rb") as b_file:

        # 1. Зчитування перших 4 байтів заголовка
        header = b_file.read(4)

        if header != FIRMWARE_MAGIC_HEADER:
            raise ValueError(
                f"Невідомий формат образу: сигнатура {header.hex().upper()} "
                f"!= {FIRMWARE_MAGIC_HEADER.hex().upper()}"
            )

        # 2. Зчитування версії (байти 4 та 5)
        version_bytes = b_file.read(2)

        if len(version_bytes) != 2:
            raise ValueError("У бінарному файлі відсутні байти версії.")

        major_ver, minor_ver = version_bytes

        # 3. Визначення повного розміру файлу
        current_pos = b_file.tell()
        file_size_bytes = b_file.seek(0, os.SEEK_END)
        payload_size = file_size_bytes - current_pos

    return {
        "magic_signature_hex": f"0x{header.hex().upper()}",
        "firmware_version": f"v{major_ver}.{minor_ver}",
        "total_image_size_bytes": file_size_bytes,
        "payload_size_bytes": payload_size,
        "is_signature_valid": True,
    }


def export_system_snapshot(
    output_json_path: Path, csv_stats: dict, bin_stats: dict
) -> None:
    """
    Серіалізує підсумковий стан системи у структурований JSON-документ.
    """
    snapshot_payload = {
        "spectrum_metadata": {
            "device_type": "Спектроаналізатор сигналу",
            "snapshot_generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pipeline_version": "1.0.0",
        },
        "spectrum_analysis_summary": csv_stats,
        "spectrum_binary_audit": bin_stats,
    }

    with open(output_json_path, mode="w", encoding="utf-8") as j_file:
        json.dump(snapshot_payload, j_file, indent=4, ensure_ascii=False)


def main() -> None:
    """Головна точка входу лабораторної роботи."""
    print("=" * 80)
    print(f"{'КОНВЕЄР ФАЙЛОВОГО ВВЕДЕННЯ-ВИВЕДЕННЯ ТА ЗБЕРЕЖЕННЯ СТАНУ':^80}")
    print("=" * 80)

    input_csv = Path("spectrum.csv")
    cleaned_csv = Path("cleaned_spectrum.csv")
    input_bin = Path("firmware_sample.bin")
    output_json = Path("station_snapshot.json")

    t_start = time.perf_counter()

    # 1. Виконання обробки CSV спектроаналізатора
    csv_metrics = process_csv_telemetry(input_csv, cleaned_csv)

    print("Обробка CSV успішна:")
    print(f"  Зчитано рядків:       {csv_metrics['total_read_rows']:>5d}")
    print(f"  Валідних рядків:      {csv_metrics['valid_saved_rows']:>5d}")
    print(f"  Відкинуто аномалій:   {csv_metrics['anomalous_rows_dropped']:>5d}")

    center = csv_metrics["central_frequency_mhz"]
    if center is not None:
        print(f"  Центральна частота:   {center:.2f} МГц")
    else:
        print("  Центральна частота:   Не визначена")

    print(f"  Файл збережено:       {cleaned_csv.name}")
    print("-" * 80)

    # 2. Виконання бінарного аудиту
    bin_metrics = verify_binary_firmware(input_bin)

    print("Аудит бінарного образу успішний:")
    print(f"  Магічна сигнатура:    {bin_metrics['magic_signature_hex']}")
    print(f"  Версія образу:        {bin_metrics['firmware_version']}")
    print(f"  Загальний розмір:     {bin_metrics['total_image_size_bytes']} байтів")
    print(f"  Розмір корисних даних: {bin_metrics['payload_size_bytes']} байтів")
    print("-" * 80)

    # 3. Серіалізація підсумкового стану у JSON
    export_system_snapshot(output_json, csv_metrics, bin_metrics)

    print("Підсумковий знімок стану збережено у JSON:")
    print(f"  Цільовий файл:        {output_json.name}")
    print("=" * 80)

    t_elapsed = time.perf_counter() - t_start
    print(f"Час виконання повного конвеєра: {t_elapsed * 1000:.3f} мс\n")


if __name__ == "__main__":
    main()
