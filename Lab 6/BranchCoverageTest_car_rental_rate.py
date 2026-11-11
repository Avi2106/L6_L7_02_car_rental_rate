import pytest

from car_rental_rate import check_fleet_telematics, process_rental_fleet


def test_validation_rejects_non_list_before_checking_fee():
    with pytest.raises(ValueError, match="Invalid rental list or admin fee"):
        process_rental_fleet("not a list", -1)


def test_validation_rejects_negative_fee_for_list():
    with pytest.raises(ValueError, match="Invalid rental list or admin fee"):
        process_rental_fleet([], -0.01)


def test_valid_empty_rentals_return_empty_batch():
    assert process_rental_fleet([], 0) == {
        "total_revenue": 0.0,
        "status": "EMPTY_BATCH",
    }


def test_unconfirmed_rentals_are_skipped():
    assert process_rental_fleet([{"is_confirmed": False}], 1) == {
        "total_revenue": 0.0,
        "status": "EMPTY_BATCH",
    }


@pytest.mark.parametrize(
    ("days", "expected_revenue", "expected_status"),
    [
        (0, 0.0, "EMPTY_BATCH"),
        (-1, 0.0, "EMPTY_BATCH"),
        (1, 40.0, "STANDARD"),
    ],
)
def test_nonpositive_and_positive_rental_durations(
    days, expected_revenue, expected_status
):
    rentals = [{"is_confirmed": True, "days": days, "driver_age": 30}]

    assert process_rental_fleet(rentals, 0) == {
        "total_revenue": expected_revenue,
        "status": expected_status,
    }


@pytest.mark.parametrize(
    ("vehicle_type", "expected_total"),
    [
        ("luxury", 120.0),
        ("suv", 70.0),
        ("standard", 40.0),
    ],
)
def test_each_vehicle_rate_selection(vehicle_type, expected_total):
    rentals = [
        {
            "is_confirmed": True,
            "vehicle_type": vehicle_type,
            "driver_age": 30,
        }
    ]

    result = process_rental_fleet(rentals, 0)

    assert result == {"total_revenue": expected_total, "status": "STANDARD"}


def test_negative_mileage_is_flagged_and_skipped():
    rentals = [
        {
            "is_confirmed": True,
            "driver_age": 30,
            "trip_segments": [-1],
        }
    ]

    assert process_rental_fleet(rentals, 0) == {
        "total_revenue": 40.0,
        "status": "STANDARD",
    }


@pytest.mark.parametrize(
    ("miles", "expected_total"),
    [(300, 100.0), (301, 160.4)],
)
def test_mileage_threshold_selects_correct_rate(miles, expected_total):
    rentals = [
        {
            "is_confirmed": True,
            "driver_age": 30,
            "trip_segments": [miles],
        }
    ]

    assert process_rental_fleet(rentals, 0) == {
        "total_revenue": expected_total,
        "status": "STANDARD",
    }


def test_driver_under_21_gets_penalty_and_stops_later_segments():
    rentals = [
        {
            "is_confirmed": True,
            "driver_age": 20,
            "trip_segments": [301, 500],
        }
    ]

    assert process_rental_fleet(rentals, 0) == {
        "total_revenue": 310.0,
        "status": "STANDARD",
    }


@pytest.mark.parametrize(
    ("driver_age", "vehicle_type", "expected_total"),
    [
        (24, "luxury", 170.0),
        (24, "economy", 60.0),
        (25, "luxury", 120.0),
    ],
)
def test_underage_and_age_boundary_surcharge_branches(
    driver_age, vehicle_type, expected_total
):
    rentals = [
        {
            "is_confirmed": True,
            "driver_age": driver_age,
            "vehicle_type": vehicle_type,
        }
    ]

    assert process_rental_fleet(rentals, 0) == {
        "total_revenue": expected_total,
        "status": "STANDARD",
    }


@pytest.mark.parametrize(
    ("risk_rentals", "expected_status", "expected_revenue"),
    [
        (4, "STANDARD", 40.0),
        (5, "HIGH_RISK_AUDIT", 0.0),
    ],
)
def test_risk_flag_threshold(risk_rentals, expected_status, expected_revenue):
    rentals = [{"is_confirmed": True, "days": 0} for _ in range(risk_rentals)]
    if risk_rentals == 4:
        rentals.append({"is_confirmed": True, "days": 1, "driver_age": 30})

    assert process_rental_fleet(rentals, 0) == {
        "total_revenue": expected_revenue,
        "status": expected_status,
    }


def test_telematics_without_data_returns_no_data():
    assert check_fleet_telematics([]) == "NO_DATA"


def test_telematics_with_no_speeding_returns_safe():
    assert check_fleet_telematics([[], [100, 90]]) == "SAFE"


def test_single_speeding_event_does_not_ground_vehicle():
    assert check_fleet_telematics([[101, 100, 102]]) == "SAFE"


def test_two_consecutive_speeding_events_ground_vehicle():
    assert check_fleet_telematics([[101, 102]]) == "GROUND_VEHICLE"


def test_speeding_streak_does_not_carry_between_vehicles():
    assert check_fleet_telematics([[101], [102]]) == "SAFE"
