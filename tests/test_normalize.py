"""Fast unit tests that don't need the dataset:  uv run pytest"""

from recipebot.data import split_steps
from recipebot.normalize import (
    canonical_names,
    clean_line,
    compare_quantity,
    family_of,
    line_categories,
    parse_quantity,
    resolve_restriction,
    singularize,
)


def test_quantities_units_and_prep_words_are_stripped():
    assert canonical_names("1 1/2 cups chopped onion") == ("onion",)
    assert canonical_names("2 cloves garlic, minced") == ("garlic",)
    assert canonical_names("1 (15 ounce) can black beans, rinsed and drained") == ("black bean",)
    assert canonical_names("4 skinless, boneless chicken breast halves ADVERTISEMENT") == ("chicken breast",)


def test_salt_and_pepper_splits_in_two():
    assert canonical_names("salt and pepper to taste") == ("salt", "black pepper")


def test_section_headers_are_not_ingredients():
    assert canonical_names("For the sauce:") == ()


def test_families_merge_varieties_but_not_products():
    assert family_of("red onion") == "onion"
    assert family_of("egg yolk") == "egg"
    assert family_of("garlic powder") == "garlic powder"
    assert family_of("green onion") == "green onion"


def test_allergen_exceptions():
    assert "dairy" not in line_categories(clean_line("2 tablespoons peanut butter"))
    assert "peanut" in line_categories(clean_line("2 tablespoons peanut butter"))
    assert "dairy" not in line_categories(clean_line("1 can coconut milk"))
    assert "egg" not in line_categories(clean_line("1 large eggplant"))
    assert "dairy" in line_categories(clean_line("1/2 cup heavy cream"))
    assert "tree_nut" not in line_categories(clean_line("1/4 tsp ground nutmeg"))
    # explicitly labelled free-from products are trusted, but only that product
    assert "dairy" not in line_categories(clean_line("1 cup shredded dairy-free mozzarella-style cheese"))
    assert "dairy" in line_categories(clean_line("1 cup vegan yogurt and 1 cup milk"))


def test_restriction_words():
    assert resolve_restriction("dairy") == (["dairy"], None)
    assert "egg" in resolve_restriction("vegan")[0]
    assert resolve_restriction("cilantro") == ([], "cilantro")


def test_singularize():
    assert singularize("tomatoes") == "tomato"
    assert singularize("berries") == "berry"
    assert singularize("asparagus") == "asparagus"


def test_quantities():
    assert parse_quantity("1 1/2 cups rice") == (1.5, "cup")
    assert parse_quantity("3 eggs") == (3.0, None)
    assert compare_quantity((3.0, None), (2.0, None)) == "enough"
    assert compare_quantity((1.0, "cup"), (20.0, "tbsp")) == "not enough"
    assert compare_quantity((2.0, "cup"), (1.0, "lb")) is None  # volume vs mass: not comparable


def test_step_rule_dedupes_and_drops_boilerplate():
    text = "Watch how to make this recipe.\nBoil water.\nAdd pasta.\nBoil water.\n"
    assert split_steps(text) == ["Boil water.", "Add pasta."]
