from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import re
import psycopg2

tokenizer = AutoTokenizer.from_pretrained("xlm-roberta-base")
model = AutoModelForSequenceClassification.from_pretrained("unsupported")


def predict_chunks(text, tokenizer, model, max_length=512, stride=50, threshold=0.9):
    # Tokenize the text
    tokens = tokenizer.tokenize(text)

    # Prepare chunks
    input_ids_list = []
    attention_mask_list = []
    text_chunks_list = []  # List to store the actual text chunks for returning with predictions

    start_idx = 0
    while start_idx < len(tokens):
        end_idx = start_idx + max_length
        tokens_chunk = tokens[start_idx:end_idx]

        text_chunk = tokenizer.convert_tokens_to_string(tokens_chunk)
        text_chunks_list.append(text_chunk)

        inputs_chunk = tokenizer.encode_plus(
            text_chunk,
            add_special_tokens=True,
            max_length=max_length,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )

        input_ids_list.append(inputs_chunk["input_ids"].squeeze())
        attention_mask_list.append(inputs_chunk["attention_mask"].squeeze())

        start_idx += stride

    chunks_results = []
    for input_ids, attention_mask, text_chunk in zip(input_ids_list, attention_mask_list, text_chunks_list):
        with torch.no_grad():
            outputs = model(input_ids.unsqueeze(0), attention_mask=attention_mask.unsqueeze(0))

        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        predicted_class = torch.argmax(probs)
        predicted_confidence = probs[0, predicted_class].item()

        chunks_results.append({
            'text_chunk': text_chunk,
            'predicted_class': predicted_class.item(),
            'predicted_confidence': predicted_confidence
        })

        # If a positive match is found with high confidence, return early
        if predicted_class == 1 and predicted_confidence > threshold:
            print(predicted_confidence)
            return chunks_results

    return chunks_results


def check_for_message(text, tokenizer, model, threshold=0.9):
    predictions = predict_chunks(text, tokenizer, model, threshold=threshold)

    for pred in predictions:
        if pred['predicted_class'] == 1:
            return 1, pred['text_chunk'], pred['predicted_confidence']
    return 0, None, 1


def classify_text():
    conn = psycopg2.connect("dbname='unsupported_crawl' user='uc_test'", port=5434)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT g.id, g.text
        FROM global_100k g
        LEFT JOIN classification_results_global crg ON g.id = crg.id
        WHERE crg.id IS NULL
        AND g.is_crawled = 1
        AND g.text != 'empty'
        AND g.is_error = 0;
    """)
    texts_data = cursor.fetchall()

    for text_id, t in texts_data:
        text = re.sub("\s+", " ", t)
        #text = text.replace("\n", " ")
        text = text.encode("utf-8", errors='ignore').decode("utf-8")

        print("id", text_id, "Text: ", text)

        contains_message, message_chunk, confidence = check_for_message(text, tokenizer, model)

        if contains_message == 1:
            print(f"The text contains an unsupported browser message in the following chunk: \"{message_chunk}\"")
        else:
            print("The text does not contain an unsupported browser message.")

        print("Predicted class: ", contains_message)

        cursor.execute("""
                INSERT INTO classification_results_global (id, is_unsupported, message_chunk, confidence)
                VALUES (%s, %s, %s, %s)
                """, (text_id, contains_message, message_chunk, confidence))
        conn.commit()

    cursor.close()
    conn.close()


if __name__ == "__main__":
    classify_text()
