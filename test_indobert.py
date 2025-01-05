import torch
from transformers import BertTokenizer, BertForMaskedLM
from dictionary_db import DictionaryDB
import re

# Initialize BERT model and tokenizer
model_name = "bert-base-multilingual-cased"
print("Loading tokenizer and model...")
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForMaskedLM.from_pretrained(model_name)
model.eval()  # Set model to evaluation mode

def get_bert_embeddings(text: str):
    """Get BERT embeddings for a given text."""
    inputs = tokenizer.encode_plus(
        text,
        add_special_tokens=True,
        max_length=512,
        padding='max_length',
        truncation=True,
        return_tensors="pt"
    )
    
    with torch.no_grad():
        outputs = model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
    
    return embeddings

def get_bert_suggestions(text: str, mask_token: str, context: str) -> list:
    """Get BERT suggestions for a masked token based on context."""
    # Replace the target word with mask token
    masked_text = text.replace(mask_token, tokenizer.mask_token)
    
    # Tokenize the masked text
    tokens = tokenizer.tokenize(masked_text)
    # Convert tokens to ids and add special tokens
    token_ids = tokenizer.convert_tokens_to_ids(tokens)
    # Prepare input tensor
    inputs = {
        "input_ids": torch.tensor([token_ids]),
        "attention_mask": torch.ones(len(token_ids)).unsqueeze(0)
    }
    
    # Find mask token position
    mask_positions = [i for i, id in enumerate(token_ids) if id == tokenizer.mask_token_id]
    if not mask_positions:
        return []
    mask_idx = mask_positions[0]
    
    # Get predictions
    with torch.no_grad():
        outputs = model(**inputs)
        predictions = outputs.logits[0, mask_idx]
        probs = torch.nn.functional.softmax(predictions, dim=-1)
        top_k = torch.topk(probs, k=10, dim=-1)
    
    # Get the predicted tokens
    filtered_predictions = []
    for score, pred_idx in zip(top_k.values, top_k.indices):
        token = tokenizer.decode([pred_idx])
        # Prefer formal words in personal context, casual words in casual context
        if context == "personal":
            if not any(casual_marker in token.lower() for casual_marker in ["gw", "lu", "elu", "gue", "loe"]):
                filtered_predictions.append(token.strip())
        else:
            filtered_predictions.append(token.strip())
            
    return filtered_predictions[:5]  # Return top 5 filtered predictions

def detect_context(text: str, db: DictionaryDB) -> str:
    """Detect the context of the text based on keywords."""
    text = text.lower()
    
    # Get context detection keywords
    formal_keywords = db.get_by_category("formal_context")
    casual_keywords = db.get_by_category("casual_context")
    
    # Count occurrences of each context
    formal_count = 0
    casual_count = 0
    
    for keyword in formal_keywords:
        if keyword["word"].lower() in text:
            formal_count += 1
            
    for keyword in casual_keywords:
        if keyword["word"].lower() in text:
            casual_count += 1
    
    # If formal/coaching keywords are found, use personal tone
    if formal_count > 0:
        return "personal"
    # If casual keywords are found or no specific context, use casual tone
    return "casual"

def translate_text(text: str, db: DictionaryDB) -> str:
    """Translate text using dictionary and make it more conversational."""
    context = detect_context(text, db)
    
    # First try to match and translate longer phrases
    translated_text = text
    phrases = db.get_by_category("phrases")
    for phrase in phrases:
        if phrase["word"].lower() in translated_text.lower():
            options = phrase["translations"]["casual"] if context == "casual" else phrase["translations"]["personal"]
            translated_text = translated_text.replace(phrase["word"], options[0])
    
    # Then handle individual words
    words = re.findall(r'\b\w+\b|[^\w\s]', translated_text)
    translated_words = []
    word_translations = {}
    
    for i, word in enumerate(words):
        # Skip punctuation
        if not word.isalnum():
            translated_words.append(word)
            continue
            
        # Check if we've already translated this word
        word_lower = word.lower()
        if word_lower in word_translations:
            translated = word_translations[word_lower]
            if word[0].isupper():
                translated = translated.capitalize()
            translated_words.append(translated)
            continue
        
        # Try dictionary translation
        translation = None
        for w in [word, word.capitalize(), word.lower()]:
            translation = db.get_translations(w)
            if translation:
                break
                
        if translation:
            # Use dictionary translation based on context
            options = translation["casual"] if context == "casual" else translation["personal"]
            translated = options[0] if isinstance(options, list) else options
        else:
            # If no translation, keep original word
            translated = word
        
        # Store translation for consistency
        word_translations[word_lower] = translated
        
        # Preserve original capitalization
        if word[0].isupper():
            translated = translated.capitalize()
        translated_words.append(translated)
    
    # Join words with proper spacing
    result = ""
    for i, word in enumerate(translated_words):
        if i > 0:
            if word.isalnum() and (translated_words[i-1].isalnum() or translated_words[i-1] in ",.!?"):
                result += " "
        result += word
    
    # Add context-specific markers based on content
    if context == "casual":
        # Get all patterns from database
        all_patterns = db.get_pattern()
        
        # Try to match patterns
        matched_pattern = None
        for pattern in all_patterns:
            if pattern["formal_pattern"].lower() in text.lower():
                matched_pattern = pattern
                break
        
        if matched_pattern:
            # Replace the formal pattern with casual pattern
            result = result.replace(
                matched_pattern["formal_pattern"].lower(),
                matched_pattern["casual_pattern"].lower()
            )
        
        # Make everything lowercase for casual context
        result = result.lower()
    else:
        # Remove any casual markers that might have slipped through
        result = result.replace("nih, ", "").replace("tuh ", "")
        if result[0].islower():
            result = result.capitalize()
    
    return result

def main():
    print("🤖 Casual Indonesian Translator")
    print("Connecting to database...")
    db = DictionaryDB()
    
    # Ensure database is connected before proceeding
    if not db.connect():
        print("Failed to connect to database. Exiting...")
        return
    
    while True:
        print("\n" + "="*50)
        text = input("✍️  Enter text (or 'exit' to quit): ").strip()
        
        if text.lower() == 'exit':
            print("\n👋 Goodbye!")
            break
        
        context = detect_context(text, db)
        print(f"\nDetected context: {context}")
        
        translated = translate_text(text, db)
        print("\n🎯 Translation:")
        print(f"→ {translated}")

if __name__ == "__main__":
    main() 