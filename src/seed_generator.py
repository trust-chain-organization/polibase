"""SEEDファイル生成モジュール"""

from datetime import datetime
from typing import TextIO

from sqlalchemy import text

from src.config.database import get_db_engine


class SeedGenerator:
    """データベースからSEEDファイルを生成するクラス"""

    def __init__(self):
        self.engine = get_db_engine()

    def generate_governing_bodies_seed(self, output: TextIO | None = None) -> str:
        """governing_bodiesテーブルのSEEDファイルを生成する"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT name, type
                    FROM governing_bodies
                    ORDER BY
                        CASE type
                            WHEN '国' THEN 1
                            WHEN '都道府県' THEN 2
                            WHEN '市町村' THEN 3
                            ELSE 4
                        END,
                        name
                """)
            )
            bodies = result.fetchall()

        lines = [
            f"-- Generated from database on "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "-- governing_bodies seed data",
            "",
            "INSERT INTO governing_bodies (name, type) VALUES",
        ]

        # タイプごとにグループ化
        grouped_data = {}
        for body in bodies:
            body_type = body["type"]
            if body_type not in grouped_data:
                grouped_data[body_type] = []
            grouped_data[body_type].append(body)

        first_group = True
        for type_name, bodies_list in grouped_data.items():
            if not first_group:
                lines.append("")
            lines.append(f"-- {type_name}")

            for i, body in enumerate(bodies_list):
                # SQLインジェクション対策のため、シングルクォートをエスケープ
                name = body["name"].replace("'", "''")
                type_val = body["type"].replace("'", "''")

                # 最後の要素かどうかチェック（全体での最後）
                is_last = (
                    type_name == list(grouped_data.keys())[-1]
                    and i == len(bodies_list) - 1
                )

                comma = "" if is_last else ","
                lines.append(f"('{name}', '{type_val}'){comma}")

            first_group = False

        lines.append("ON CONFLICT (name, type) DO NOTHING;")

        result = "\n".join(lines)
        if output:
            output.write(result)
        return result

    def generate_conferences_seed(self, output: TextIO | None = None) -> str:
        """conferencesテーブルのSEEDファイルを生成する"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        c.name,
                        c.type,
                        gb.name as governing_body_name,
                        gb.type as governing_body_type
                    FROM conferences c
                    JOIN governing_bodies gb ON c.governing_body_id = gb.id
                    ORDER BY
                        CASE gb.type
                            WHEN '国' THEN 1
                            WHEN '都道府県' THEN 2
                            WHEN '市町村' THEN 3
                            ELSE 4
                        END,
                        gb.name,
                        c.name
                """)
            )
            conferences = result.fetchall()

        lines = [
            f"-- Generated from database on "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "-- conferences seed data",
            "",
            "INSERT INTO conferences (name, type, governing_body_id) VALUES",
        ]

        # 開催主体ごとにグループ化
        grouped_data = {}
        for conf in conferences:
            key = f"{conf['governing_body_type']}_{conf['governing_body_name']}"
            if key not in grouped_data:
                grouped_data[key] = {
                    "body_name": conf["governing_body_name"],
                    "body_type": conf["governing_body_type"],
                    "conferences": [],
                }
            grouped_data[key]["conferences"].append(conf)

        first_group = True
        group_keys = list(grouped_data.keys())
        for group_idx, (_key, data) in enumerate(grouped_data.items()):
            body_name = data["body_name"]
            body_type = data["body_type"]
            confs = data["conferences"]

            if not first_group:
                lines.append("")
            lines.append(f"-- {body_name} ({body_type})")

            for i, conf in enumerate(confs):
                # SQLインジェクション対策のため、シングルクォートをエスケープ
                conf_name = conf["name"].replace("'", "''")
                body_name_escaped = body_name.replace("'", "''")
                body_type_escaped = body_type.replace("'", "''")

                # 最後の要素かどうかチェック（全体での最後）
                is_last = group_idx == len(group_keys) - 1 and i == len(confs) - 1

                comma = "" if is_last else ","

                if conf.get("type"):
                    conf_type = conf["type"].replace("'", "''")
                    lines.append(
                        f"('{conf_name}', '{conf_type}', "
                        f"(SELECT id FROM governing_bodies WHERE name = "
                        f"'{body_name_escaped}' AND type = '{body_type_escaped}')"
                        f"){comma}"
                    )
                else:
                    lines.append(
                        f"('{conf_name}', NULL, "
                        f"(SELECT id FROM governing_bodies WHERE name = "
                        f"'{body_name_escaped}' AND type = '{body_type_escaped}')"
                        f"){comma}"
                    )

            first_group = False

        lines.append("ON CONFLICT (name, governing_body_id) DO NOTHING;")

        result = "\n".join(lines)
        if output:
            output.write(result)
        return result

    def generate_political_parties_seed(self, output: TextIO | None = None) -> str:
        """political_partiesテーブルのSEEDファイルを生成する"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT name
                    FROM political_parties
                    ORDER BY name
                """)
            )
            parties = result.fetchall()

        lines = [
            f"-- Generated from database on "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "-- political_parties seed data",
            "",
            "INSERT INTO political_parties (name) VALUES",
        ]

        for i, party in enumerate(parties):
            # SQLインジェクション対策のため、シングルクォートをエスケープ
            name = party["name"].replace("'", "''")
            comma = "" if i == len(parties) - 1 else ","
            lines.append(f"('{name}'){comma}")

        lines.append("ON CONFLICT (name) DO NOTHING;")

        result = "\n".join(lines)
        if output:
            output.write(result)
        return result


def generate_all_seeds(output_dir: str = "database") -> None:
    """すべてのSEEDファイルを生成する"""
    import os

    generator = SeedGenerator()

    # ディレクトリが/で終わっている場合は削除
    output_dir = output_dir.rstrip("/")

    # governing_bodies
    path = os.path.join(output_dir, "seed_governing_bodies_generated.sql")
    with open(path, "w") as f:
        generator.generate_governing_bodies_seed(f)
        print(f"Generated: {path}")

    # conferences
    path = os.path.join(output_dir, "seed_conferences_generated.sql")
    with open(path, "w") as f:
        generator.generate_conferences_seed(f)
        print(f"Generated: {path}")

    # political_parties
    path = os.path.join(output_dir, "seed_political_parties_generated.sql")
    with open(path, "w") as f:
        generator.generate_political_parties_seed(f)
        print(f"Generated: {path}")


if __name__ == "__main__":
    generate_all_seeds()
