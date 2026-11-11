import pytest

from car_rental_rate import check_fleet_telematics, process_rental_fleet


def test_rejects_non_list_rentals():
    with pytest.raises(ValueError, match="Invalid rental list or admin fee"):
        process_rental_fleet(None, 0)


def test_rejects_negative_admin_fee():
    with pytest.raises(ValueError, match="Invalid rental list or admin fee"):
        process_rental_fleet([], -0.01)


def test_empty_batch_has_empty_status():
    assert process_rental_fleet([], 0) == {
        "total_revenue": 0.0,
        "status": "EMPTY_BATCH",
    }


def test_unconfirmed_rental_is_skipped():
    result = process_rental_fleet([{"is_confirmed": False}], 10)

    assert result == {"total_revenue": 0.0, "status": "EMPTY_BATCH"}


def test_confirmed_rental_uses_default_values():
    result = process_rental_fleet([{"is_confirmed": True}], 5)

    assert result == {"total_revenue": 45.0, "status": "STANDARD"}


@pytest.mark.parametrize(
    ("vehicle_type", "expected_total"),
    [
        ("luxury", 250.0),
        ("suv", 150.0),
        ("economy", 90.0),
        ("van", 90.0),
    ],
)
def test_vehicle_rates_and_unknown_type_fallback(vehicle_type, expected_total):
    rentals = [
        {
            "is_confirmed": True,
            "vehicle_type": vehicle_type,
            "driver_age": 30,
            "days": 2,
        }
    ]

    result = process_rental_fleet(rentals, 10)

    assert result == {"total_revenue": expected_total, "status": "STANDARD"}


def test_zero_day_rental_is_flagged_and_not_charged():
    result = process_rental_fleet(
        [{"is_confirmed": True, "days": 0}],
        0,
    )

    assert result == {"total_revenue": 0.0, "status": "EMPTY_BATCH"}


def test_negative_and_boundary_mileage_segments():
    rentals = [
        {
            "is_confirmed": True,
            "driver_age": 30,
            "days": 1,
            "trip_segments": [-1, 0, 300],
        }
    ]

    result = process_rental_fleet(rentals, 0)

    assert result == {"total_revenue": 100.0, "status": "STANDARD"}


def test_long_trip_uses_standard_high_mileage_charge():
    rentals = [
        {
            "is_confirmed": True,
            "driver_age": 30,
            "days": 1,
            "trip_segments": [301],
        }
    ]

    result = process_rental_fleet(rentals, 0)

    assert result == {"total_revenue": 160.4, "status": "STANDARD"}


def test_under_21_long_trip_adds_penalty_and_stops_processing_segments():
    rentals = [
        {
            "is_confirmed": True,
            "driver_age": 20,
            "days": 1,
            "trip_segments": [301, 999],
        }
    ]

    result = process_rental_fleet(rentals, 0)

    assert result == {"total_revenue": 310.0, "status": "STANDARD"}


@pytest.mark.parametrize(
    ("vehicle_type", "expected_total"),
    [("luxury", 345.0), ("economy", 125.0)],
)
def test_under_25_surcharge_depends_on_vehicle_type(vehicle_type, expected_total):
    rentals = [
        {
            "is_confirmed": True,
            "vehicle_type": vehicle_type,
            "driver_age": 24,
            "days": 2,
        }
    ]

    result = process_rental_fleet(rentals, 5)

    assert result == {"total_revenue": expected_total, "status": "STANDARD"}


def test_age_25_does_not_receive_underage_surcharge():
    rentals = [
        {
            "is_confirmed": True,
            "vehicle_type": "luxury",
            "driver_age": 25,
            "days": 1,
        }
    ]

    result = process_rental_fleet(rentals, 0)

    assert result == {"total_revenue": 120.0, "status": "STANDARD"}


def test_four_risk_flags_do_not_trigger_high_risk_audit():
    rentals = [
        {"is_confirmed": True, "days": 0},
        {"is_confirmed": True, "days": 0},
        {"is_confirmed": True, "days": 0},
        {"is_confirmed": True, "days": 0},
        {"is_confirmed": True, "days": 1, "driver_age": 30},
    ]

    result = process_rental_fleet(rentals, 0)

    assert result == {"total_revenue": 40.0, "status": "STANDARD"}


def test_more_than_four_risk_flags_trigger_high_risk_audit():
    rentals = [{"is_confirmed": True, "days": 0} for _ in range(5)]

    result = process_rental_fleet(rentals, 0)

    assert result == {"total_revenue": 0.0, "status": "HIGH_RISK_AUDIT"}


@pytest.mark.parametrize("telematics_matrix", [None, []])
def test_empty_telematics_data_returns_no_data(telematics_matrix):
    assert check_fleet_telematics(telematics_matrix) == "NO_DATA"


def test_no_speeding_or_empty_vehicle_logs_are_safe():
    assert check_fleet_telematics([[], [100, 80, 100]]) == "SAFE"


def test_one_speeding_event_is_safe():
    assert check_fleet_telematics([[101]]) == "SAFE"


def test_two_consecutive_speeding_events_ground_vehicle():
    assert check_fleet_telematics([[101, 102]]) == "GROUND_VEHICLE"


def test_normal_speed_resets_speeding_streak():
    assert check_fleet_telematics([[101, 100, 102]]) == "SAFE"
