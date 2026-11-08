from __future__ import annotations

import re
from functools import lru_cache


_UNICODE_FRACTIONS = {
    "½": " 1/2", "¼": " 1/4", "¾": " 3/4", "⅓": " 1/3", "⅔": " 2/3",
    "⅛": " 1/8", "⅜": " 3/8", "⅝": " 5/8", "⅞": " 7/8", "⅕": " 1/5",
}

UNITS = {
    "cup", "cups", "c", "tablespoon", "tablespoons", "tbsp", "tbsps", "tbs", "tbl", "tbls",
    "teaspoon", "teaspoons", "tsp", "tsps", "ounce", "ounces", "oz", "fluid", "fl",
    "pound", "pounds", "lb", "lbs", "gram", "grams", "g", "kilogram", "kilograms", "kg",
    "ml", "milliliter", "milliliters", "millilitre", "millilitres", "liter", "liters",
    "litre", "litres", "l", "quart", "quarts", "qt", "pint", "pints", "pt", "gallon",
    "gallons", "pinch", "pinches", "dash", "dashes", "clove", "cloves", "can", "cans",
    "package", "packages", "pkg", "packet", "packets", "jar", "jars", "bottle", "bottles",
    "box", "boxes", "bag", "bags", "container", "containers", "bunch", "bunches", "sprig",
    "sprigs", "stalk", "stalks", "slice", "slices", "stick", "sticks", "head", "heads",
    "piece", "pieces", "handful", "handfuls", "envelope", "envelopes", "drop", "drops",
    "scoop", "scoops", "carton", "cartons", "loaf", "loaves", "rib", "ribs", "ear", "ears",
    "inch", "inches", "cube", "cubes", "sheet", "sheets", "strip", "strips", "wedge", "wedges",
}

DESCRIPTORS = {
    "fresh", "freshly", "chopped", "finely", "coarsely", "roughly", "minced", "diced",
    "sliced", "thinly", "thickly", "cubed", "grated", "shredded", "peeled", "seeded",
    "deveined", "trimmed", "halved", "quartered", "softened", "melted", "beaten", "lightly",
    "well", "divided", "packed", "firmly", "loosely", "sifted", "rinsed", "drained",
    "cooked", "uncooked", "large", "small", "medium", "extra-large", "jumbo", "boneless",
    "skinless", "ripe", "cold", "warm", "room", "temperature", "thawed", "organic",
    "optional", "about", "approximately", "plus", "more", "taste", "garnish", "needed",
    "dried", "low-sodium", "reduced-sodium", "sodium", "low-fat", "reduced-fat", "fat-free",
    "nonfat", "non-fat", "lowfat", "skim", "light", "dark", "unsalted", "salted", "good",
    "quality", "best", "pure", "prepared", "store-bought", "homemade", "chilled", "cut",
    "into", "pieces", "piece", "bite-size", "bite-sized", "inch", "or", "the", "a",
    "an", "for", "to", "in", "at", "such", "as", "very", "fine", "coarse", "freshly-ground",
    "torn", "smashed", "crumbled", "julienned", "mashed", "toasted", "roasted", "lean",
    "extra", "whole", "head", "heads", "stemmed", "pitted", "hulled", "cored", "zested",
    "squeezed", "juiced", "heaping", "level", "scant", "generous", "additional", "serving",
    "frozen", "canned", "raw", "plain", "regular", "favorite", "your", "any", "other",
    "mixed", "assorted", "thick", "thin", "into", "lengthwise", "crosswise", "unpeeled",
    "unbleached", "bleached", "sweetened", "unsweetened", "condensed", "spray", "low-salt",
    "nonstick", "non-stick",
}

_GROUND_KEEP = {"beef", "pork", "turkey", "chicken", "lamb", "veal", "meat", "sausage", "ginger", "bison"}

_IRREGULAR_PLURALS = {
    "leaves": "leaf", "loaves": "loaf", "halves": "half", "potatoes": "potato",
    "tomatoes": "tomato", "mangoes": "mango", "cookies": "cookie", "brownies": "brownie",
    "chilies": "chili", "chillies": "chili", "chiles": "chili", "chile": "chili",
    "anchovies": "anchovy", "knives": "knife", "calves": "calf",
}
_NO_SINGULAR = {
    "asparagus", "couscous", "hummus", "molasses", "swiss", "brussels", "bass", "grass",
    "watercress", "citrus", "octopus", "lentils", "grits", "oats", "greens", "series",
    "schnapps", "hummous", "chips", "noodles", "peas", "beans", "sprouts", "capers",
    "jus", "anise", "cress", "lettuce", "tortellini", "ravioli", "gnocchi", "fries",
}


def singularize(word: str) -> str:
    if word in _IRREGULAR_PLURALS:
        return _IRREGULAR_PLURALS[word]
    if len(word) <= 3 or word in _NO_SINGULAR:
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("oes"):
        return word[:-2]
    if word.endswith(("ches", "shes", "sses", "xes", "zes")):
        return word[:-2]
    if word.endswith(("ss", "us", "is")):
        return word
    if word.endswith("s"):
        return word[:-1]
    return word


def singular_phrase(phrase: str) -> str:
    words = phrase.split()
    if not words:
        return phrase
    last = words[-1]
    if last in {"beans", "peas", "noodles", "sprouts", "capers", "chips", "oats"}:
        words[-1] = last[:-1]
    else:
        words[-1] = singularize(last)
    return " ".join(words)


_QTY_RE = re.compile(r"^(?:\d+(?:[.,/]\d+)?|\d+\s+\d+/\d+|[-–]|to|or|x)\b\s*")
_PAREN_RE = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_SPACES = re.compile(r"\s+")


def clean_line(line: str) -> str:
    if not line:
        return ""
    text = line.replace("ADVERTISEMENT", " ")
    for k, v in _UNICODE_FRACTIONS.items():
        text = text.replace(k, v)
    text = text.lower().replace("’", "'").replace("–", "-").replace("—", "-")
    return _SPACES.sub(" ", text).strip()


def is_header(line: str) -> bool:
    stripped = line.strip()
    return stripped.endswith(":") or (stripped.isupper() and len(stripped.split()) <= 4)


def _strip_quantity_and_unit(text: str) -> str:
    text = _PAREN_RE.sub(" ", text)
    text = _SPACES.sub(" ", text).strip()
    for _ in range(4):
        before = text
        while True:
            m = _QTY_RE.match(text)
            if not m or m.end() == 0:
                break
            text = text[m.end():]
        parts = text.split(" ", 1)
        if parts and parts[0].rstrip(".") in UNITS:
            text = parts[1] if len(parts) > 1 else ""
        if text.startswith("of "):
            text = text[3:]
        text = text.strip(" -.,")
        if text == before:
            break
    return text


SYNONYMS = {
    "scallion": "green onion", "spring onion": "green onion",
    "all-purpose flour": "flour", "all purpose flour": "flour", "plain flour": "flour",
    "white flour": "flour", "flour all-purpose": "flour", "all-purpose": "flour",
    "white sugar": "sugar", "granulated sugar": "sugar", "caster sugar": "sugar",
    "superfine sugar": "sugar", "granulated white sugar": "sugar", "cane sugar": "sugar",
    "kosher salt": "salt", "sea salt": "salt", "table salt": "salt", "salt kosher": "salt",
    "fine sea salt": "salt", "flaky sea salt": "salt",
    "pepper": "black pepper", "ground black pepper": "black pepper", "ground pepper": "black pepper",
    "cracked black pepper": "black pepper", "black peppercorn": "black pepper",
    "freshly ground black pepper": "black pepper", "fresh ground black pepper": "black pepper",
    "ground black": "black pepper", "black": "black pepper",
    "extra-virgin olive oil": "olive oil", "extra virgin olive oil": "olive oil",
    "virgin olive oil": "olive oil", "olive oil extra-virgin": "olive oil",
    "garlic clove": "garlic", "clove garlic": "garlic", "garlic glove": "garlic",
    "cloves garlic": "garlic", "clove of garlic": "garlic", "cloves of garlic": "garlic",
    "basil leaf": "basil", "thyme leaf": "thyme", "mint leaf": "mint", "sage leaf": "sage",
    "rosemary leaf": "rosemary", "oregano leaf": "oregano", "tarragon leaf": "tarragon",
    "dill weed": "dill", "thyme sprig": "thyme", "rosemary sprig": "rosemary",
    "cayenne": "cayenne pepper", "ginger root": "ginger", "gingerroot": "ginger",
    "fresh ginger": "ginger", "low-salt chicken broth": "chicken broth",
    "nonstick cooking": "cooking spray", "half and half": "half-and-half",
    "egg yolk": "egg yolk", "yolk": "egg yolk", "egg white": "egg white",
    "heavy whipping cream": "heavy cream", "whipping cream": "heavy cream",
    "double cream": "heavy cream", "cream heavy": "heavy cream",
    "confectioners' sugar": "powdered sugar", "confectioners sugar": "powdered sugar",
    "icing sugar": "powdered sugar", "confectioner's sugar": "powdered sugar",
    "parmigiano-reggiano": "parmesan cheese", "parmigiano reggiano": "parmesan cheese",
    "parmigiano-reggiano cheese": "parmesan cheese", "parmigiano reggiano cheese": "parmesan cheese",
    "parmesan": "parmesan cheese", "grated parmesan": "parmesan cheese",
    "chicken stock": "chicken broth", "beef stock": "beef broth", "vegetable stock": "vegetable broth",
    "coriander leaf": "cilantro", "cilantro leaf": "cilantro", "flat-leaf parsley": "parsley",
    "italian parsley": "parsley", "flat leaf parsley": "parsley", "parsley leaf": "parsley",
    "bicarbonate of soda": "baking soda", "cornflour": "cornstarch", "corn starch": "cornstarch",
    "chicken breast half": "chicken breast", "chicken breast halve": "chicken breast",
    "green bell pepper": "bell pepper", "red bell pepper": "bell pepper",
    "yellow bell pepper": "bell pepper", "orange bell pepper": "bell pepper",
    "green pepper": "bell pepper", "sweet pepper": "bell pepper",
    "crushed red pepper": "red pepper flakes", "crushed red pepper flake": "red pepper flakes",
    "red pepper flake": "red pepper flakes", "chili flake": "red pepper flakes",
    "dry white wine": "white wine", "dry red wine": "red wine",
    "lemon, juiced": "lemon juice", "juice of lemon": "lemon juice", "juice of lime": "lime juice",
    "ground cinnamon": "cinnamon", "cinnamon stick": "cinnamon", "ground cumin": "cumin",
    "cumin seed": "cumin", "ground nutmeg": "nutmeg", "ground cloves": "cloves",
    "ground clove": "cloves", "ground allspice": "allspice", "ground coriander": "coriander",
    "ground turmeric": "turmeric", "ground cardamom": "cardamom", "ground paprika": "paprika",
    "ice water": "water", "hot water": "water", "cold water": "water", "warm water": "water",
    "boiling water": "water", "lukewarm water": "water", "tap water": "water",
    "large egg": "egg", "egg, beaten": "egg", "whole egg": "egg",
    "penne pasta": "penne", "penne rigate": "penne", "spaghetti pasta": "spaghetti",
    "unsalted butter": "butter", "salted butter": "butter", "stick butter": "butter",
    "butter, softened": "butter", "sweet butter": "butter",
    "mayo": "mayonnaise", "ketchup": "ketchup", "catsup": "ketchup",
    "long-grain rice": "rice", "long grain rice": "rice", "white rice": "white rice",
    "plum tomato": "plum tomato", "canned tomato": "tomato", "tomato, chopped": "tomato",
    "yellow onion": "onion", "white onion": "onion", "spanish onion": "onion",
    "sweet onion": "onion", "vidalia onion": "onion", "onion, chopped": "onion",
    "sharp cheddar cheese": "cheddar cheese", "cheddar": "cheddar cheese",
    "sharp cheddar": "cheddar cheese", "mild cheddar cheese": "cheddar cheese",
    "mozzarella": "mozzarella cheese", "part-skim mozzarella cheese": "mozzarella cheese",
    "feta": "feta cheese", "ricotta": "ricotta cheese",
    "ground beef chuck": "ground beef", "ground chuck": "ground beef", "hamburger": "ground beef",
    "nonstick cooking spray": "cooking spray", "vegetable oil cooking spray": "cooking spray",
    "cooking": "cooking spray", "nonstick": "cooking spray", "vegetable cooking": "cooking spray",
    "low-sodium soy sauce": "soy sauce", "lite soy sauce": "soy sauce",
    "unsweetened cocoa powder": "cocoa powder", "cocoa": "cocoa powder",
    "pure vanilla extract": "vanilla extract", "vanilla": "vanilla extract",
    "vanilla bean": "vanilla bean", "baking powder": "baking powder",
    "whole milk": "milk", "skim milk": "milk", "2% milk": "milk", "low-fat milk": "milk",
    "fat-free milk": "milk", "nonfat milk": "milk", "1% milk": "milk",
    "lemon zest": "lemon zest", "grated lemon zest": "lemon zest", "lemon peel": "lemon zest",
    "grated lemon peel": "lemon zest", "zest of lemon": "lemon zest",
}

FAMILIES = {
    "red onion": "onion", "onion": "onion", "shallot": "shallot",
    "cherry tomato": "tomato", "grape tomato": "tomato", "roma tomato": "tomato",
    "plum tomato": "tomato", "heirloom tomato": "tomato", "beefsteak tomato": "tomato",
    "roma (plum) tomato": "tomato", "vine-ripened tomato": "tomato", "tomato": "tomato",
    "diced tomato": "tomato", "crushed tomato": "tomato", "whole tomato": "tomato",
    "russet potato": "potato", "yukon gold potato": "potato", "red potato": "potato",
    "new potato": "potato", "baking potato": "potato", "idaho potato": "potato",
    "fingerling potato": "potato", "red-skinned potato": "potato",
    "chicken breast": "chicken", "chicken thigh": "chicken", "chicken wing": "chicken",
    "chicken leg": "chicken", "chicken drumstick": "chicken", "chicken tender": "chicken",
    "chicken tenderloin": "chicken", "whole chicken": "chicken", "chicken meat": "chicken",
    "rotisserie chicken": "chicken", "chicken breast fillet": "chicken", "broiler-fryer chicken": "chicken",
    "egg yolk": "egg", "egg white": "egg", "egg": "egg", "hard-boiled egg": "egg",
    "white rice": "rice", "brown rice": "rice", "basmati rice": "rice", "jasmine rice": "rice",
    "long-grain white rice": "rice", "long grain white rice": "rice", "arborio rice": "rice",
    "instant rice": "rice", "short-grain rice": "rice", "rice": "rice", "sushi rice": "rice",
    "enriched white rice": "rice", "parboiled rice": "rice",
    "bell pepper": "bell pepper", "garlic": "garlic", "clove": "cloves",
    "green onion": "green onion", "lemon": "lemon", "lime": "lime",
    "carrot": "carrot", "baby carrot": "carrot", "celery rib": "celery", "celery stalk": "celery",
    "celery": "celery", "spinach": "spinach", "baby spinach": "spinach",
    "jalapeno pepper": "jalapeno", "jalapeño pepper": "jalapeno", "jalapeno": "jalapeno",
    "jalapeño": "jalapeno", "banana": "banana", "ripe banana": "banana",
    "mushroom": "mushroom", "button mushroom": "mushroom", "white mushroom": "mushroom",
    "cremini mushroom": "mushroom", "baby bella mushroom": "mushroom",
    "penne": "penne", "spaghetti": "spaghetti", "salmon fillet": "salmon", "salmon": "salmon",
}


def _drop_descriptors(segment: str) -> str:
    words = segment.split()
    out = []
    for i, w in enumerate(words):
        w = w.strip(".;*")
        if not w:
            continue
        if w == "ground":
            nxt = words[i + 1] if i + 1 < len(words) else ""
            if singularize(nxt) in _GROUND_KEEP:
                out.append(w)
            continue
        if w in DESCRIPTORS or re.fullmatch(r"[\d/.\-]+", w):
            continue
        out.append(w)
    while out and out[0] in {"and", "of", "&"}:
        out.pop(0)
    while out and out[-1] in {"and", "of", "&"}:
        out.pop()
    return " ".join(out)


@lru_cache(maxsize=300_000)
def canonical_names(line: str) -> tuple[str, ...]:
    text = clean_line(line)
    if not text or is_header(line.replace("ADVERTISEMENT", "")):
        return ()
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    text = _strip_quantity_and_unit(text)
    text = re.sub(r"\b(to taste|for garnish|for serving|as needed|or more|or to taste|if desired)\b", " ", text)

    low = text.strip()
    if re.match(r"^(kosher |sea )?salt (and|&) (freshly |fresh )?(ground |cracked )?(black )?pepper", low):
        return ("salt", "black pepper")

    low = re.split(r"\bor\b|/", low)[0]

    segments = [s.strip() for s in low.split(",")]
    name = ""
    for seg in segments:
        cand = _drop_descriptors(seg)
        if cand:
            name = cand
            break
    if not name:
        return ()
    name = name.strip(" -'\"")
    name = singular_phrase(name)
    name = SYNONYMS.get(name, name)
    if len(name) < 2 or len(name) > 60 or name in UNITS:
        return ()
    return (name,)


def family_of(name: str) -> str:
    if name in FAMILIES:
        return FAMILIES[name]
    m = re.fullmatch(r"(?:red|yellow|white|sweet|vidalia|spanish|maui|walla walla) onion", name)
    if m:
        return "onion"
    m = re.fullmatch(r"(?:[a-z\-]+ )?(?:cherry|grape|roma|plum|heirloom) tomato", name)
    if m:
        return "tomato"
    return name


DIFFERENT_PRODUCTS = {
    "green onion", "spring onion", "french-fried onion", "fried onion", "french fried onion",
    "sweet potato", "peanut butter", "apple butter", "almond butter", "cocoa butter",
    "cashew butter", "nut butter", "sunflower butter", "coconut milk", "almond milk",
    "soy milk", "rice milk", "oat milk", "cashew milk", "coconut cream", "sour cream",
    "ice cream", "vanilla ice cream", "whipped cream", "wild rice", "cauliflower rice",
    "vanilla bean", "coffee bean", "jelly bean", "candy corn", "sun-dried tomato",
    "sun dried tomato", "oil-packed sun-dried tomato", "egg substitute", "brown sugar",
    "powdered sugar", "garlic powder", "onion powder", "chicken bouillon", "chicken broth",
    "vegetable broth", "beef broth", "cream of tartar", "tomato paste", "tomato sauce",
    "light brown sugar", "dark brown sugar", "golden brown sugar", "coconut sugar", "maple sugar",
    "chocolate chip cookie", "egg roll wrapper",
}


def normalize_user_ingredient(text: str) -> str:
    names = canonical_names(text)
    if not names:
        names = (singular_phrase(clean_line(text)),)
    return family_of(names[0])


CATEGORY_TERMS: dict[str, list[str]] = {
    "dairy": [
        "milk", "butter", "buttermilk", "cream", "creamer", "cheese", "cheddar", "mozzarella",
        "parmesan", "parmigiano", "ricotta", "feta", "gouda", "brie", "camembert", "mascarpone",
        "yogurt", "yoghurt", "ghee", "whey", "casein", "half-and-half", "half and half",
        "creme fraiche", "crème fraîche", "custard", "ice cream", "kefir", "paneer", "queso",
        "gruyere", "gruyère", "provolone", "romano", "asiago", "monterey jack", "colby",
        "pecorino", "fontina", "havarti", "emmental", "manchego", "cotija", "neufchatel",
        "evaporated milk", "condensed milk", "alfredo", "velveeta", "cheez", "bechamel",
    ],
    "egg": ["egg", "eggs", "yolk", "yolks", "mayonnaise", "mayo", "meringue", "eggnog", "aioli"],
    "peanut": ["peanut", "peanuts", "groundnut", "groundnuts"],
    "tree_nut": [
        "almond", "almonds", "walnut", "walnuts", "pecan", "pecans", "cashew", "cashews",
        "pistachio", "pistachios", "hazelnut", "hazelnuts", "macadamia", "brazil nut",
        "pine nut", "pine nuts", "pignoli", "chestnut", "chestnuts", "praline", "marzipan",
        "nutella", "nut", "nuts", "amaretto", "frangipane",
    ],
    "gluten": [
        "flour", "wheat", "bread", "breadcrumbs", "bread crumbs", "crumbs", "pasta", "spaghetti",
        "penne", "macaroni", "linguine", "fettuccine", "lasagna", "noodle", "noodles", "couscous",
        "bulgur", "barley", "rye", "semolina", "farro", "spelt", "seitan", "soy sauce", "teriyaki",
        "beer", "ale", "malt", "cracker", "crackers", "biscuit", "biscuits", "pie crust", "pastry",
        "tortilla", "tortillas", "pita", "croutons", "panko", "orzo", "cake mix", "wonton",
        "phyllo", "filo", "graham", "rigatoni", "ziti", "rotini", "farfalle", "gnocchi", "ravioli",
        "tortellini", "dumpling", "baguette", "roll", "rolls", "bun", "buns", "croissant",
        "muffin", "pretzel", "cookie", "cookies", "cake", "brownie", "stuffing", "bisquick",
    ],
    "meat": [
        "beef", "pork", "chicken", "turkey", "lamb", "veal", "bacon", "ham", "sausage",
        "sausages", "pepperoni", "salami", "prosciutto", "pancetta", "chorizo", "steak", "duck",
        "venison", "goose", "meat", "meatballs", "gelatin", "lard", "hot dog", "hot dogs",
        "bratwurst", "kielbasa", "brisket", "ribs", "sirloin", "tenderloin", "roast", "mutton",
        "goat", "rabbit", "quail", "pheasant", "bison", "oxtail", "liver", "giblets", "bouillon",
        "drippings", "suet", "andouille", "mortadella", "corned beef", "pastrami", "jerky",
    ],
    "fish": [
        "fish", "salmon", "tuna", "cod", "tilapia", "halibut", "trout", "anchovy", "anchovies",
        "sardine", "sardines", "mackerel", "snapper", "swordfish", "catfish", "haddock",
        "flounder", "sole", "bass", "mahi", "fish sauce", "worcestershire", "caviar", "roe",
    ],
    "shellfish": [
        "shrimp", "prawn", "prawns", "crab", "crabmeat", "lobster", "scallop", "scallops", "clam",
        "clams", "mussel", "mussels", "oyster", "oysters", "squid", "calamari", "octopus",
        "crawfish", "crayfish", "langoustine",
    ],
    "pork": [
        "pork", "bacon", "ham", "prosciutto", "pancetta", "chorizo", "salami", "pepperoni",
        "lard", "sausage", "sausages", "andouille", "kielbasa", "mortadella", "hot dog",
    ],
    "alcohol": [
        "wine", "beer", "rum", "vodka", "whiskey", "whisky", "bourbon", "brandy", "sherry",
        "liqueur", "tequila", "gin", "sake", "mirin", "champagne", "cognac", "kahlua",
        "amaretto", "marsala", "vermouth", "port", "prosecco", "ale", "stout", "schnapps",
        "grand marnier", "triple sec", "cointreau", "bitters",
    ],
    "soy": ["soy", "soya", "tofu", "edamame", "miso", "tempeh", "tamari", "soybean", "soybeans"],
}

CATEGORY_EXCEPTIONS: dict[str, list[str]] = {
    "dairy": [
        "coconut milk", "coconut cream", "almond milk", "soy milk", "soymilk", "oat milk",
        "rice milk", "cashew milk", "hemp milk", "peanut butter", "almond butter", "cashew butter",
        "nut butter", "apple butter", "cocoa butter", "sunflower butter", "sunbutter",
        "cream of tartar", "cream of coconut", "dairy-free", "non-dairy", "nondairy", "vegan",
        "butter lettuce", "butter beans", "butter bean", "milk-free", "coconut yogurt",
        "soy yogurt", "creamed corn", "ice cream salt", "cream soda",
    ],
    "egg": ["eggplant", "egg replacer", "egg-free", "vegan mayonnaise", "egg roll wrapper free"],
    "peanut": [],
    "tree_nut": ["nutmeg", "coconut", "butternut", "doughnut", "donut", "nut-free", "water chestnut", "water chestnuts", "pine nut free", "nutritional yeast"],
    "gluten": [
        "gluten-free", "gluten free", "almond flour", "rice flour", "coconut flour", "corn flour",
        "chickpea flour", "potato flour", "tapioca flour", "buckwheat", "corn tortilla",
        "corn tortillas", "rice noodle", "rice noodles", "cornbread mix free", "breadfruit",
        "tamari", "rice paper", "cornstarch", "glass noodles", "shirataki", "arrowroot",
        "egg roll", "cake flour free", "sorghum flour", "oat flour", "cassava flour",
        "roll out", "rolled oats", "pork roll",
    ],
    "meat": [
        "vegetable broth", "vegetable bouillon", "vegetable stock", "meatless", "veggie",
        "vegetarian", "imitation", "mushroom broth", "coconut meat", "crab meat",
        "beefsteak tomato", "roasted", "roast pepper", "nut meat", "walnut meat",
        "agar", "plant-based", "soy chorizo", "tofu",
    ],
    "fish": ["fish-free", "vegan worcestershire"],
    "shellfish": [],
    "pork": ["pork-free", "turkey bacon", "turkey ham", "turkey sausage", "chicken sausage", "veggie"],
    "alcohol": ["wine vinegar", "sherry vinegar", "rice wine vinegar", "cider vinegar", "non-alcoholic", "ginger ale", "root beer", "ginger beer", "malt vinegar", "port-salut"],
    "soy": [],
}

DIET_ALIASES: dict[str, list[str]] = {
    "dairy": ["dairy"], "dairy-free": ["dairy"], "lactose": ["dairy"], "milk": ["dairy"],
    "egg": ["egg"], "eggs": ["egg"], "egg-free": ["egg"],
    "peanut": ["peanut"], "peanuts": ["peanut"],
    "nut": ["peanut", "tree_nut"], "nuts": ["peanut", "tree_nut"], "nut-free": ["peanut", "tree_nut"],
    "tree nut": ["tree_nut"], "tree nuts": ["tree_nut"], "tree_nut": ["tree_nut"],
    "gluten": ["gluten"], "gluten-free": ["gluten"], "wheat": ["gluten"],
    "meat": ["meat", "fish", "shellfish"], "vegetarian": ["meat", "fish", "shellfish"],
    "vegan": ["meat", "fish", "shellfish", "dairy", "egg", "honey"],
    "pescatarian": ["meat"], "fish": ["fish"], "seafood": ["fish", "shellfish"],
    "shellfish": ["shellfish"], "pork": ["pork"], "halal": ["pork", "alcohol"],
    "alcohol": ["alcohol"], "soy": ["soy"], "honey": ["honey"],
}
CATEGORY_TERMS["honey"] = ["honey"]
CATEGORY_EXCEPTIONS["honey"] = ["honeydew"]


def _compile(terms: list[str]) -> re.Pattern:
    alts = sorted({re.escape(t) for t in terms}, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(alts) + r")(?:e?s)?\b")


_CAT_RE = {c: _compile(t) for c, t in CATEGORY_TERMS.items()}
_EXC_RE = {c: (_compile(t) if t else None) for c, t in CATEGORY_EXCEPTIONS.items()}

ALL_CATEGORIES = list(CATEGORY_TERMS)


_FREE_LABEL_RX = {
    "dairy": re.compile(r"\b(?:dairy[- ]free|non[- ]?dairy|vegan|plant[- ]based)\s+(?:[\w-]+\s+){0,2}"
                        r"(?:cheese|butter|milk|cream|yogurt|yoghurt|sour cream|cream cheese|parmesan|mozzarella)\b"),
    "egg": re.compile(r"\b(?:egg[- ]free|eggless|vegan)\s+(?:[\w-]+\s+){0,2}(?:mayonnaise|mayo|egg substitute|egg replacer)\b"),
}


def line_categories(clean: str) -> set[str]:
    hits = set()
    for cat, rx in _CAT_RE.items():
        text = clean
        if cat in _FREE_LABEL_RX:
            text = _FREE_LABEL_RX[cat].sub(" ", text)
        exc = _EXC_RE.get(cat)
        if exc is not None:
            text = exc.sub(" ", text)
        if rx.search(text):
            hits.add(cat)
    return hits


def term_regex(term: str) -> re.Pattern:
    t = clean_line(term)
    base = singular_phrase(t)
    alts = {re.escape(t), re.escape(base)}
    return re.compile(r"\b(?:" + "|".join(sorted(alts, key=len, reverse=True)) + r")(?:e?s)?\b")


def resolve_restriction(word: str) -> tuple[list[str], str | None]:
    w = clean_line(word).replace("no ", "").replace("-free", "").replace(" free", "").strip()
    if w in DIET_ALIASES:
        return DIET_ALIASES[w], None
    if w + "-free" in DIET_ALIASES:
        return DIET_ALIASES[w + "-free"], None
    return [], w


_UNIT_CANON = {
    "cup": "cup", "cups": "cup", "c": "cup",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp": "tbsp", "tbs": "tbsp", "tbl": "tbsp",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsp": "tsp",
    "ounce": "oz", "ounces": "oz", "oz": "oz", "pound": "lb", "pounds": "lb", "lb": "lb",
    "lbs": "lb", "gram": "g", "grams": "g", "g": "g", "kilogram": "kg", "kilograms": "kg",
    "kg": "kg", "ml": "ml", "liter": "l", "liters": "l", "litre": "l", "litres": "l", "l": "l",
}
_TO_BASE = {
    "tsp": ("volume", 1.0), "tbsp": ("volume", 3.0), "cup": ("volume", 48.0),
    "ml": ("volume", 0.2029), "l": ("volume", 202.9),
    "g": ("mass", 1.0), "kg": ("mass", 1000.0), "oz": ("mass", 28.35), "lb": ("mass", 453.6),
    None: ("count", 1.0),
}


def _parse_number(tok: str) -> float | None:
    try:
        if " " in tok:
            whole, frac = tok.split(" ", 1)
            return float(whole) + _parse_number(frac)
        if "/" in tok:
            a, b = tok.split("/")
            return float(a) / float(b)
        return float(tok)
    except (ValueError, ZeroDivisionError, TypeError):
        return None


_AMOUNT_RE = re.compile(r"^\s*(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*([a-z]+)?")


def parse_quantity(line: str) -> tuple[float | None, str | None]:
    text = _PAREN_RE.sub(" ", clean_line(line))
    m = _AMOUNT_RE.match(text)
    if not m:
        return None, None
    amount = _parse_number(m.group(1))
    unit = _UNIT_CANON.get(m.group(2) or "", None)
    return amount, unit


def compare_quantity(have: tuple, need: tuple) -> str | None:
    (ha, hu), (na, nu) = have, need
    if ha is None or na is None:
        return None
    if hu not in _TO_BASE or nu not in _TO_BASE:
        return None
    hd, hf = _TO_BASE[hu]
    nd, nf = _TO_BASE[nu]
    if hd != nd:
        return None
    return "enough" if ha * hf >= na * nf - 1e-9 else "not enough"
