from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

class DictionaryDB:
    def __init__(self):
        self.connection_url = "mongodb://administrator:GarapinCloud2024Jun@192.168.8.35:32001/?directConnection=true&authSource=admin"
        self.client = None
        self.db = None
        self.dictionary = None
        self.patterns = None  # New collection for sentence patterns
        
    def connect(self):
        try:
            self.client = MongoClient(self.connection_url, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            print("Successfully connected to MongoDB!")
            
            self.db = self.client['raku']
            self.dictionary = self.db['dictionary']
            self.patterns = self.db['patterns']  # Initialize patterns collection
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"Could not connect to MongoDB: {e}")
            return False

    def add_word(self, word, casual_translations, personal_translations, category):
        """
        Add a new word to the dictionary
        """
        if self.dictionary is None:
            self.connect()
        try:
            # Check if word already exists
            existing = self.dictionary.find_one({"word": word})
            if existing:
                print(f"Word '{word}' already exists in dictionary")
                return True
                
            word_entry = {
                "word": word,
                "translations": {
                    "casual": casual_translations,
                    "personal": personal_translations
                },
                "category": category
            }
            self.dictionary.insert_one(word_entry)
            print(f"Successfully added word: {word}")
            return True
        except Exception as e:
            print(f"Error adding word: {e}")
            return False

    def update_word(self, word, casual_translations=None, personal_translations=None, category=None):
        """
        Update an existing word's translations or category
        """
        if self.dictionary is None:
            self.connect()
        try:
            update_fields = {}
            if casual_translations is not None:
                update_fields["translations.casual"] = casual_translations
            if personal_translations is not None:
                update_fields["translations.personal"] = personal_translations
            if category is not None:
                update_fields["category"] = category
            
            if update_fields:
                self.dictionary.update_one(
                    {"word": word},
                    {"$set": update_fields}
                )
                print(f"Successfully updated word: {word}")
                return True
        except Exception as e:
            print(f"Error updating word: {e}")
            return False

    def delete_word(self, word):
        """
        Delete a word from the dictionary
        """
        if self.dictionary is None:
            self.connect()
        try:
            result = self.dictionary.delete_one({"word": word})
            if result.deleted_count > 0:
                print(f"Successfully deleted word: {word}")
                return True
            print(f"Word not found: {word}")
            return False
        except Exception as e:
            print(f"Error deleting word: {e}")
            return False

    def get_by_category(self, category):
        """
        Retrieve all words belonging to a specific category
        """
        if self.dictionary is None:
            self.connect()
        try:
            results = self.dictionary.find({"category": category})
            return list(results)
        except Exception as e:
            print(f"Error retrieving words by category: {e}")
            return []

    def get_translations(self, word):
        """
        Get translations for a specific word
        """
        if self.dictionary is None:
            self.connect()
        try:
            result = self.dictionary.find_one({"word": word})
            return result["translations"] if result else None
        except Exception as e:
            print(f"Error retrieving translations: {e}")
            return None

    def add_pattern(self, pattern_type, formal_pattern, casual_pattern, examples=None):
        """
        Add a new sentence pattern to the patterns collection
        """
        if self.patterns is None:
            self.connect()
        try:
            # Check if pattern already exists
            existing = self.patterns.find_one({"pattern_type": pattern_type, "formal_pattern": formal_pattern})
            if existing:
                print(f"Pattern '{pattern_type}:{formal_pattern}' already exists")
                return True
                
            pattern_entry = {
                "pattern_type": pattern_type,
                "formal_pattern": formal_pattern,
                "casual_pattern": casual_pattern,
                "examples": examples or []
            }
            self.patterns.insert_one(pattern_entry)
            print(f"Successfully added pattern: {pattern_type}")
            return True
        except Exception as e:
            print(f"Error adding pattern: {e}")
            return False

    def get_pattern(self, pattern_type=None, formal_pattern=None):
        """
        Get patterns from the database
        """
        if self.patterns is None:
            self.connect()
        try:
            query = {}
            if pattern_type:
                query["pattern_type"] = pattern_type
            if formal_pattern:
                query["formal_pattern"] = formal_pattern
            
            results = self.patterns.find(query)
            return list(results)
        except Exception as e:
            print(f"Error retrieving patterns: {e}")
            return []

def main():
    db = DictionaryDB()
    if db.connect():
        # Clear existing entries
        db.dictionary.drop()
        db.patterns.drop()
        print("Cleared existing dictionary and pattern entries")
        
        # Add sentence patterns
        patterns = [
            {
                "type": "starter",
                "formal": "jika",
                "casual": "kalo",
                "examples": ["Jika Anda -> Kalo lu"]
            },
            {
                "type": "starter",
                "formal": "kalau",
                "casual": "kalo",
                "examples": ["Kalau Anda -> Kalo lu"]
            },
            {
                "type": "starter",
                "formal": "apabila",
                "casual": "kalo",
                "examples": ["Apabila Anda -> Kalo lu"]
            },
            {
                "type": "question",
                "formal": "bagaimana",
                "casual": "gimana",
                "examples": ["Bagaimana cara -> Gimana cara"]
            },
            {
                "type": "question",
                "formal": "mengapa",
                "casual": "kenapa",
                "examples": ["Mengapa tidak -> Kenapa ngga"]
            },
            {
                "type": "ability",
                "formal": "saya dapat",
                "casual": "gue bisa",
                "examples": ["Saya dapat membantu -> Gue bisa bantu"]
            },
            {
                "type": "ability",
                "formal": "saya bisa",
                "casual": "gue bisa",
                "examples": ["Saya bisa menjelaskan -> Gue bisa jelasin"]
            }
        ]
        
        for pattern in patterns:
            db.add_pattern(pattern["type"], pattern["formal"], pattern["casual"], pattern["examples"])
        
        # Dictionary of all words to add
        words = {
            "pronouns": {
                "saya": (["gue", "gw"], ["aku"]),
                "kamu": (["lu", "elo"], ["kamu"]),
                "Anda": (["lu", "elo"], ["kamu"]),
                "anda": (["lu", "elo"], ["kamu"])
            },
            "phrases": {
                "tindakan yang disarankan": (["yang disaranin"], ["yang disarankan"]),
                "ini berarti": (["maksudnya tuh"], ["ini artinya"]),
                "tujuan hidup": (["cita-cita"], ["tujuan hidup"]),
                "langkah ini berguna": (["ini berguna"], ["ini berguna"]),
                "mencari tahu": (["nyari"], ["mencari"]),
                "langkah-langkah": (["cara-cara"], ["langkah-langkah"])
            },
            "verbs": {
                "mengevaluasi": (["mikirin"], ["memikirkan"]),
                "mempertimbangkan": (["pikirin"], ["pikirkan"]),
                "dapat": (["bisa"], ["dapat"]),
                "pelajari": (["pelajarin"], ["pelajari"]),
                "meningkatkan": (["ningkatin"], ["meningkatkan"])
            },
            "nouns": {
                "karier": (["kerjaan"], ["karir"]),
                "pencapaian": (["pencapaian"], ["pencapaian"]),
                "keterampilan": (["skill"], ["kemampuan"]),
                "pekerjaan": (["kerjaan"], ["pekerjaan"]),
                "tahun": (["taun"], ["tahun"]),
                "langkah": (["cara"], ["langkah"]),
                "pengembangan pribadi": (["pengembangan diri"], ["pengembangan pribadi"]),
                "pengembangan profesional": (["pengembangan karir"], ["pengembangan profesional"])
            },
            "prepositions": {
                "untuk": (["buat"], ["untuk"]),
                "melalui": (["lewat"], ["melalui"]),
                "di": (["di"], ["di"])
            },
            "conjunctions": {
                "atau": (["ato"], ["atau"]),
                "dan": (["sama"], ["dan"]),
                "yang": (["yang"], ["yang"])
            },
            "adjectives": {
                "baru": (["baru"], ["baru"]),
                "berguna": (["berguna"], ["berguna"])
            },
            "context_markers": {
                "evaluasi": (["evaluasi"], ["evaluasi"]),
                "tujuan": (["tujuan"], ["tujuan"]),
                "profesional": (["profesional"], ["profesional"]),
                "pengembangan": (["pengembangan"], ["pengembangan"]),
                "disarankan": (["disarankan"], ["disarankan"]),
                "ngobrol": (["ngobrol"], ["berbicara"]),
                "santai": (["santai"], ["rileks"])
            }
        }
        
        # Add all words from the dictionary
        added_words = set()  # Keep track of added words
        for category, word_dict in words.items():
            for word, (casual, personal) in word_dict.items():
                if word.lower() not in added_words:  # Only add if not already added
                    db.add_word(word, casual, personal, category)
                    added_words.add(word.lower())

if __name__ == "__main__":
    main() 