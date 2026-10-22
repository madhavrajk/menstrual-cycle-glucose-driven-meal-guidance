import pytest

from mealguide.guidance.portions import daily_target, meal_targets, ree, scale_factor


def test_mifflin_st_jeor_female():
    # 10*60 + 6.25*165 - 5*25 - 161
    assert ree(60, 165, 25) == pytest.approx(1345.25)


def test_maintain_range_is_plus_minus_ten_percent():
    t = daily_target(60, 165, 25, activity="moderate")
    assert t.target == round(1345.25 * 1.55)
    assert t.low == pytest.approx(t.target * 0.9, abs=1)
    assert t.high == pytest.approx(t.target * 1.1, abs=1)


def test_deficit_is_capped_at_500():
    t = daily_target(60, 165, 25, activity="moderate", goal="lose")
    assert t.target == round(1345.25 * 1.55 - 500)


def test_never_below_resting_needs():
    t = daily_target(60, 165, 25, activity="sedentary", goal="lose")  # TDEE - 500 < REE
    assert t.target == t.ree and t.low >= t.ree
    assert any("resting needs" in n for n in t.notes)


def test_no_weight_loss_when_underweight():
    t = daily_target(48, 170, 22, goal="lose")  # BMI about 16.6
    assert t.target == t.tdee
    assert any("BMI" in n for n in t.notes)


def test_luteal_upper_is_off_by_default():
    base = daily_target(60, 165, 25)
    assert daily_target(60, 165, 25, luteal=True).target == base.target
    assert daily_target(60, 165, 25, luteal=True, luteal_upper=True).target == base.high


def test_meal_split_adds_up():
    m = meal_targets(2000, meals=3, snacks=1)
    assert m["snack"] == 200 and m["meal"] == 600


@pytest.mark.parametrize("kcal,slot,expected", [(400, 600, 1.5), (600, 600, 1.0),
                                                (150, 600, 2.0), (900, 300, 0.5)])
def test_scale_factor_rounds_and_clamps(kcal, slot, expected):
    assert scale_factor(kcal, slot) == expected


def test_rejects_out_of_range_inputs():
    with pytest.raises(ValueError):
        ree(60, 165, 15)
    with pytest.raises(ValueError):
        daily_target(60, 165, 25, activity="couch")
