"""
Generate SEED data for governing_bodies table from city_and_prefecture_code.csv
"""

import csv
from pathlib import Path


def parse_organization_type(code: str, prefecture_name: str, city_name: str) -> str:
    """
    Determine organization type based on the code and names

    Based on the specification:
    - 1st and 2nd digits: Prefecture code
    - 3rd, 4th, and 5th digits: Municipality code (000 for prefectures)
    - 6th digit: Check digit
    """
    municipality_code = code[2:5]

    # Prefecture level (municipality code is 000)
    if municipality_code == "000":
        return "都道府県"

    # City level - need to check the name for specific types
    if not city_name:
        return "市町村"

    # Check for specific administrative divisions
    if city_name.endswith("区"):
        # Special wards in Tokyo, designated cities' wards
        if prefecture_name == "東京都":
            return "特別区"
        else:
            return "区"
    elif city_name.endswith("市"):
        return "市"
    elif city_name.endswith("町"):
        return "町"
    elif city_name.endswith("村"):
        return "村"
    elif city_name.endswith("郡"):
        return "郡"
    else:
        return "市町村"


def main():
    # Get the project root directory
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent

    csv_path = project_root / "data" / "city_and_prefecture_code.csv"
    output_path = (
        project_root / "database" / "seed_governing_bodies_all_municipalities.sql"
    )

    # Read the CSV file
    governing_bodies = []
    seen_codes = set()
    seen_names = set()  # Track (name, type) pairs to avoid duplicates

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        # Skip header
        next(reader)

        for row in reader:
            if len(row) < 5:
                continue

            code = row[0]
            prefecture_name = row[1]
            city_name = row[2]

            # Skip if code is already processed
            if code in seen_codes:
                continue
            seen_codes.add(code)

            # Determine organization type
            org_type = parse_organization_type(code, prefecture_name, city_name)

            # Determine name and type for the record
            if city_name:
                # Municipality level
                # For special wards (特別区), use just the name
                if org_type == "特別区":
                    name = city_name
                else:
                    # For other municipalities, prepend prefecture name
                    # to ensure uniqueness
                    name = f"{prefecture_name}{city_name}"
                type_value = "市町村"
            else:
                # Prefecture level
                name = prefecture_name
                type_value = "都道府県"

            # Check if this name/type combination already exists
            name_type_key = (name, type_value)
            if name_type_key in seen_names:
                # If duplicate, append the code to make it unique
                name = f"{name} ({code})"
            seen_names.add(name_type_key)

            governing_bodies.append(
                {
                    "name": name,
                    "type": type_value,
                    "organization_code": code,
                    "organization_type": org_type,
                }
            )

    # Generate SQL file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(
            "-- SEED data for governing_bodies table with all Japanese municipalities\n"
        )
        f.write("-- Generated from city_and_prefecture_code.csv\n\n")

        f.write("-- Insert all local governments with organization codes\n")
        f.write(
            "INSERT INTO governing_bodies "
            "(name, type, organization_code, organization_type) VALUES\n"
        )

        values = []
        for gb in governing_bodies:
            # Escape single quotes for SQL
            name_escaped = gb["name"].replace("'", "''")
            value = (
                f"('{name_escaped}', '{gb['type']}', "
                f"'{gb['organization_code']}', '{gb['organization_type']}')"
            )
            values.append(value)

        f.write(",\n".join(values))
        f.write("\nON CONFLICT (name, type) DO UPDATE SET\n")
        f.write("    organization_code = EXCLUDED.organization_code,\n")
        f.write("    organization_type = EXCLUDED.organization_type,\n")
        f.write("    updated_at = CURRENT_TIMESTAMP;\n")

    print(f"Generated SEED file with {len(governing_bodies)} governing bodies")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
