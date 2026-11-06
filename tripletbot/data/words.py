"""Static content: word banks and trivia. English only."""
from __future__ import annotations

# --------------------------------------------------------------- Wordle (5)
FIVE_LETTER = """
about above actor acute admit adopt adult after again agent agree ahead alarm album alert alike alive
allow alone along alter among anger angle angry ankle apart apple apply arena argue arise armor arrow
aside asset audio avoid awake award aware badly baked baker basic basil beach beard beast began begin
being belly below bench berry birth black blade blame blank blast blaze bleak blend bless blind block
blood bloom blown board boast bonus boost booth bound brain brake brand brave bread break breed brick
brief bring broad broke brown brush build built bunch burnt burst buyer cabin cable camel candy canal
cargo carry carve catch cause cease chain chair chalk charm chart chase cheap check cheer chess chest
chief child chill china choir chose chunk cider cigar civic claim clamp clash class clean clear clerk
click cliff climb cling cloak clock clone close cloth cloud clown coach coast cobra cocoa colon color
comet comic coral corner costa couch cough could count court cover crack craft crane crash crate crawl
crazy cream creek creep crest crime crisp cross crowd crown crude cruel crush crust curve cycle daily
dairy daisy dance dated dealt death debut decay decor delay delta dense depth derby devil diary dirty
disco ditch diver dizzy dodge doing donor doubt dough dozen draft drain drama drank drawn dream dress
dried drift drill drink drive drone drove drown drums dryer dusty dwarf eager eagle early earth easel
eight elbow elder elect elite email empty enemy enjoy enter entry equal equip erase error essay event
every exact exams exist extra fable faced fairy faith false fancy fatal fault favor feast fence ferry
fetch fever fiber field fiery fifth fifty fight final find first flag flame flash fleet flesh float
flock flood floor flour fluid flush flute flying focus foggy force forge forty forum found frame fraud
fresh fried frost fruit fully funny gauge ghost giant given giver glad glass gleam globe gloom glory
glove going grace grade grain grand grant grape graph grasp grass grave great greed green greet grill
grind groan groom group grove growl grown guard guess guest guide guild guilt habit handy happy harsh
hatch haunt heart heavy hedge hello hence hobby honey honor horse hotel house hover human humor hurry
ideal image imply index inner input irony issue ivory jelly jewel joint joker judge juice jumbo juror
karma kayak knee kneel knife knock known label labor lance large laser later laugh layer learn lease
least leave legal lemon level lever light limit linen liner links lions liver lobby local lodge logic
loose lorry lover lower loyal lucky lunar lunch lyric magic magma major maker mango maple march marsh
match maybe mayor medal media melon mercy merge merit merry metal meter micro midst might minor minus
model moist money month moral motor mount mouse mouth movie mucus mural music nasal naval nerve never
newly night noble noise north notch novel nurse nylon oasis ocean offer often olive onion opera orbit
order organ other otter ought ounce outer owner oxide ozone paint panel panic paper party pasta patch
pause peace peach pearl pedal penny perch phase phone photo piano piece pilot pinch pitch pixel pizza
place plain plane plank plant plate plaza plead pluck plumb point polar porch pouch pound power press
price pride prime print prior prize probe proof proud prove prune pulse punch pupil puppy purse quake
queen query quest queue quick quiet quilt quirk quota quote radar radio raise rally ranch range rapid
ratio raven reach react ready realm rebel refer regal relax relay renew repay reply rerun reset resin
rhyme rider ridge rifle right rigid rinse ripen risen risky rival river roast robin robot rocky rogue
roman rough round route royal rugby ruler rumor rural sadly salad salon salsa salty sandy sauce saved
scale scalp scare scarf scene scent scoop scope score scout scrap screw scrub seize sense serum serve
seven shall shame shape share shark sharp shave sheep sheet shelf shell shift shine shirt shock shoot
shore short shout shown shrub sight silly since siren sixth sixty skate skill skirt skull slate slave
sleek sleep slice slide slope small smart smash smell smile smoke snack snake sneak sniff snow soap
soccer sober solar solid solve sorry sound south space spare spark speak spear speed spell spend spent
spice spike spill spine split spoke spoon sport spray squad squat stack staff stage stair stake stall
stamp stand stare start state stays steak steal steam steel steep steer stern stick still stock stone
stood stool store storm story stove strap straw strip stuck study stuff stump style sugar suite sunny
super sushi swamp swarm swear sweat sweep sweet swell swift swing sword syrup table taken tally tango
taste teach tempo tenant tenth thank theft their theme there these thick thief thigh thing think third
those three throw thumb tiger tight timer tired title toast today token tonic tooth topic torch total
touch tough towel tower toxic trace track trade trail train trait tramp trash treat trend trial tribe
trick tried trout truck truly trump trunk trust truth tulip tumor tulip twist typer ultra uncle under
unify union unite unity until upper upset urban usage usual utter vague valid value valve vapor vault
venue verse video vigor villa vinyl viral virus visit vital vivid vocal vodka voice voter wagon waist
waltz waste watch water weary weave wedge weigh weird whale wheat wheel where which while whisk white
whole whose widen width witch woman world worry worse worst worth would wound wrist write wrong yacht
yearn yeast yield young yours youth zebra zesty
""".split()

FIVE_LETTER = [w for w in FIVE_LETTER if len(w) == 5]

# ------------------------------------------------- Hangman (word, hint)
HANGMAN_WORDS = [
    ("planet", "Space"), ("guitar", "Music"), ("volcano", "Nature"), ("penguin", "Animals"),
    ("bicycle", "Transport"), ("diamond", "Gems"), ("library", "Places"), ("holiday", "Travel"),
    ("pyramid", "History"), ("whisper", "Verbs"), ("magnet", "Science"), ("saxophone", "Music"),
    ("rainbow", "Weather"), ("igloo", "Homes"), ("kangaroo", "Animals"), ("lantern", "Objects"),
    ("octopus", "Sea life"), ("jupiter", "Space"), ("cactus", "Plants"), ("wallet", "Objects"),
    ("glacier", "Nature"), ("monsoon", "Weather"), ("compass", "Tools"), ("tornado", "Weather"),
    ("puzzle", "Games"), ("sandwich", "Food"), ("hammock", "Objects"), ("telescope", "Science"),
    ("biscuit", "Food"), ("chimney", "Homes"), ("festival", "Culture"), ("gorilla", "Animals"),
    ("harbour", "Places"), ("javelin", "Sports"), ("kettle", "Kitchen"), ("mermaid", "Myth"),
    ("nectar", "Nature"), ("orchard", "Places"), ("peacock", "Animals"), ("quartz", "Gems"),
    ("rocket", "Space"), ("saddle", "Objects"), ("treasure", "Adventure"), ("umbrella", "Objects"),
    ("village", "Places"), ("wizard", "Myth"), ("yogurt", "Food"), ("zeppelin", "Transport"),
    ("archer", "Sports"), ("butterfly", "Animals"), ("carousel", "Places"), ("dolphin", "Sea life"),
    ("emerald", "Gems"), ("firework", "Festivals"), ("goldfish", "Animals"), ("hedgehog", "Animals"),
    ("island", "Places"), ("jellyfish", "Sea life"), ("keyboard", "Technology"), ("lighthouse", "Places"),
    ("mountain", "Nature"), ("notebook", "Objects"), ("obsidian", "Gems"), ("parachute", "Transport"),
    ("quicksand", "Nature"), ("raspberry", "Food"), ("scorpion", "Animals"), ("thunder", "Weather"),
    ("universe", "Space"), ("violin", "Music"), ("windmill", "Places"), ("xylophone", "Music"),
    ("yodel", "Music"), ("zeppelin", "Transport"), ("asteroid", "Space"), ("blizzard", "Weather"),
    ("cinnamon", "Food"), ("dragonfly", "Animals"), ("eclipse", "Space"), ("flamingo", "Animals"),
    ("galaxy", "Space"), ("horizon", "Nature"), ("iceberg", "Nature"), ("jungle", "Nature"),
    ("koala", "Animals"), ("lava", "Nature"), ("meteor", "Space"), ("nebula", "Space"),
]

# ------------------------------------------------------- Scramble (word, hint)
SCRAMBLE_WORDS = [
    ("keyboard", "Technology"), ("elephant", "Animals"), ("triangle", "Math"), ("sandwich", "Food"),
    ("airplane", "Transport"), ("birthday", "Celebrations"), ("chocolate", "Food"), ("dinosaur", "History"),
    ("umbrella", "Weather"), ("festival", "Culture"), ("hospital", "Places"), ("language", "Culture"),
    ("mountain", "Nature"), ("notebook", "School"), ("password", "Technology"), ("question", "Grammar"),
    ("restaurant", "Food"), ("swimming", "Sports"), ("treasure", "Adventure"), ("vacation", "Travel"),
    ("adventure", "Fun"), ("basketball", "Sports"), ("crocodile", "Animals"), ("detective", "Stories"),
    ("furniture", "Homes"), ("generation", "People"), ("happiness", "Feelings"), ("invisible", "Adjectives"),
    ("jellybean", "Food"), ("knowledge", "School"), ("landscape", "Nature"), ("motorcycle", "Transport"),
    ("nightmare", "Stories"), ("operation", "Medicine"), ("pineapple", "Food"), ("quotation", "Grammar"),
    ("rainforest", "Nature"), ("strawberry", "Food"), ("telephone", "Technology"), ("university", "School"),
    ("volleyball", "Sports"), ("watermelon", "Food"), ("xylophone", "Music"), ("yesterday", "Time"),
    ("zeppelin", "Transport"), ("astronaut", "Space"), ("butterfly", "Animals"), ("chameleon", "Animals"),
    ("dragonfly", "Animals"), ("explosion", "Science"), ("fireworks", "Celebrations"), ("goldenrod", "Plants"),
    ("honeycomb", "Nature"), ("invention", "Science"), ("jewellery", "Fashion"), ("kaleidoscope", "Objects"),
    ("lighthouse", "Places"), ("macaroni", "Food"), ("navigation", "Travel"), ("octopus", "Sea life"),
    ("parachute", "Transport"), ("quicksilver", "Metal"), ("raspberry", "Food"), ("submarine", "Transport"),
    ("telescope", "Science"), ("underwater", "Nature"), ("vegetable", "Food"), ("whirlpool", "Nature"),
]

# ------------------------------------------------ Trivia (q, options, answer)
TRIVIA = [
    ("Which planet is known as the Red Planet?", ["Venus", "Mars", "Jupiter", "Mercury"], 1),
    ("How many continents are there on Earth?", ["5", "6", "7", "8"], 2),
    ("What is the largest ocean?", ["Atlantic", "Indian", "Arctic", "Pacific"], 3),
    ("Which language has the most native speakers?", ["English", "Mandarin", "Spanish", "Hindi"], 1),
    ("What year did the first human land on the Moon?", ["1965", "1969", "1972", "1959"], 1),
    ("Which animal is the fastest on land?", ["Lion", "Cheetah", "Horse", "Greyhound"], 1),
    ("What is the chemical symbol for gold?", ["Ag", "Au", "Go", "Gd"], 1),
    ("How many strings does a standard guitar have?", ["4", "5", "6", "7"], 2),
    ("Which country invented pizza as we know it?", ["Greece", "France", "Italy", "Spain"], 2),
    ("What is the tallest mountain on Earth?", ["K2", "Kilimanjaro", "Everest", "Denali"], 2),
    ("Which gas do plants absorb?", ["Oxygen", "Nitrogen", "Carbon dioxide", "Helium"], 2),
    ("Who painted the Mona Lisa?", ["Michelangelo", "Da Vinci", "Raphael", "Van Gogh"], 1),
    ("What is the hardest natural substance?", ["Gold", "Iron", "Diamond", "Quartz"], 2),
    ("Which sport uses a shuttlecock?", ["Tennis", "Badminton", "Squash", "Cricket"], 1),
    ("How many players are on a football (soccer) team on the field?", ["9", "10", "11", "12"], 2),
    ("What is the capital of Japan?", ["Osaka", "Kyoto", "Tokyo", "Seoul"], 2),
    ("Which blood type is the universal donor?", ["A+", "AB-", "O-", "B+"], 2),
    ("What is the largest desert in the world?", ["Sahara", "Gobi", "Antarctic", "Mojave"], 2),
    ("How many sides does a hexagon have?", ["5", "6", "7", "8"], 1),
    ("Which organ pumps blood through the body?", ["Liver", "Lungs", "Heart", "Kidney"], 2),
    ("In which country would you find the Eiffel Tower?", ["Italy", "Belgium", "France", "Switzerland"], 2),
    ("What does 'HTTP' stand for?", ["HyperText Transfer Protocol", "High Tech Transfer Process", "Hyperlink Text Type Protocol", "Host Transfer Text Program"], 0),
    ("Which planet has the most moons?", ["Earth", "Mars", "Jupiter", "Saturn"], 3),
    ("What is the smallest prime number?", ["0", "1", "2", "3"], 2),
    ("Which element has the symbol 'O'?", ["Gold", "Osmium", "Oxygen", "Oganesson"], 2),
    ("How many minutes are in a full day?", ["1200", "1440", "1800", "2400"], 1),
    ("What is the main ingredient in guacamole?", ["Tomato", "Avocado", "Pea", "Cucumber"], 1),
    ("Who wrote 'Romeo and Juliet'?", ["Dickens", "Shakespeare", "Tolstoy", "Hemingway"], 1),
    ("Which sea creature has three hearts?", ["Shark", "Octopus", "Dolphin", "Jellyfish"], 1),
    ("What is the currency of Brazil?", ["Peso", "Real", "Escudo", "Dollar"], 1),
    ("Which is the largest mammal?", ["Elephant", "Blue whale", "Giraffe", "Orca"], 1),
    ("How many degrees are in a right angle?", ["45", "60", "90", "180"], 2),
    ("What is the fastest bird in a dive?", ["Eagle", "Falcon", "Swift", "Albatross"], 1),
    ("Which country has the most time zones?", ["Russia", "USA", "France", "China"], 2),
    ("What does 'CPU' stand for?", ["Central Processing Unit", "Computer Power Unit", "Core Program Utility", "Central Program User"], 0),
    ("Which vitamin does sunlight help produce?", ["Vitamin A", "Vitamin B12", "Vitamin C", "Vitamin D"], 3),
    ("How many bones are in the adult human body?", ["186", "206", "226", "246"], 1),
    ("What is the largest internal organ?", ["Heart", "Liver", "Lungs", "Brain"], 1),
    ("Which chess piece can jump over others?", ["Bishop", "Rook", "Knight", "Queen"], 2),
    ("Which planet is closest to the Sun?", ["Venus", "Mercury", "Earth", "Mars"], 1),
    ("What is the longest river in the world?", ["Amazon", "Nile", "Yangtze", "Mississippi"], 1),
    ("Who developed the theory of relativity?", ["Newton", "Einstein", "Galileo", "Tesla"], 1),
    ("Which fruit has the most vitamin C per 100g?", ["Orange", "Lemon", "Guava", "Apple"], 2),
    ("What is the study of stars called?", ["Geology", "Astronomy", "Biology", "Ecology"], 1),
    ("How many colours are in a rainbow?", ["5", "6", "7", "8"], 2),
    ("Which is the only mammal that can truly fly?", ["Flying squirrel", "Bat", "Sugar glider", "Colugo"], 1),
    ("What is the capital of Australia?", ["Sydney", "Melbourne", "Canberra", "Perth"], 2),
    ("Which metal is liquid at room temperature?", ["Mercury", "Lead", "Tin", "Zinc"], 0),
    ("In Minecraft, what do you need to mine diamond ore?", ["Stone pickaxe", "Iron pickaxe", "Golden pickaxe", "Wooden pickaxe"], 1),
    ("What is the most spoken language in South America?", ["Spanish", "Portuguese", "English", "Quechua"], 1),
    ("Which shape has all sides equal and all angles 90°?", ["Rectangle", "Rhombus", "Square", "Trapezoid"], 2),
    ("How many hearts does an earthworm have?", ["1", "3", "5", "7"], 2),
    ("What does 'GPU' mostly handle?", ["Storage", "Graphics", "Network", "Cooling"], 1),
    ("Which country is home to the kangaroo?", ["New Zealand", "Australia", "South Africa", "Chile"], 1),
    ("What is the boiling point of water at sea level (°C)?", ["90", "100", "110", "120"], 1),
    ("Which artist cut off part of his own ear?", ["Picasso", "Van Gogh", "Dali", "Monet"], 1),
    ("What is a group of wolves called?", ["Herd", "Pack", "Flock", "School"], 1),
    ("Which planet spins on its side?", ["Neptune", "Uranus", "Saturn", "Venus"], 1),
    ("What is the largest species of shark?", ["Great white", "Whale shark", "Tiger shark", "Hammerhead"], 1),
    ("How many keys does a standard piano have?", ["66", "76", "88", "96"], 2),
    ("Which gas makes up most of Earth's atmosphere?", ["Oxygen", "Nitrogen", "Argon", "Carbon dioxide"], 1),
    ("What does the 'www' in a URL stand for?", ["World Wide Web", "Wide Web World", "Web World Wide", "World Web Wide"], 0),
    ("Which is the coldest continent?", ["Europe", "Asia", "Antarctica", "North America"], 2),
    ("What is 7 × 8?", ["54", "56", "58", "64"], 1),
    ("Which superhero is known as the Dark Knight?", ["Superman", "Batman", "Iron Man", "Spider-Man"], 1),
]
