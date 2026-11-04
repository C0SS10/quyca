from quyca.parsers import affiliation_parser


def test_location_filter_value_is_the_normalized_label_whatever_the_db_order():
    mapping = {"Cartagena de Indias": "Cartagena"}
    rows = [{"_id": "Cartagena de Indias", "count": 30}, {"_id": "Cartagena", "count": 7}]

    for ordered_rows in (rows, rows[::-1]):
        parsed = affiliation_parser.parse_affiliation_location_filter(ordered_rows, mapping)
        assert parsed == [{"count": 37, "label": "Cartagena", "value": "Cartagena"}]
