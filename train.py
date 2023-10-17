import spacy
import json
import random
from spacy.training.example import Example
from spacy.training.iob_utils import offsets_to_biluo_tags
# Load a blank English model
nlp = spacy.blank("en")

# Create a new entity recognizer and add it to the pipeline
ner = nlp.add_pipe("ner")

# Define the labels for your entities
labels = ["NAME", "COMPANY", "PHONE", "BUDGET", "COUNTRY"]
for label in labels:
    ner.add_label(label)

# Load your training data from ner_dataset.json
with open("ner_dataset.json", "r") as f:
    training_data = json.load(f)

# Convert the training data to spaCy training examples
train_examples = []
for example in training_data:
    #text = "Hello, I am John Doe from ABC Inc in the USA. You can reach me at +123 456 7890. Our budget is around 20k - 40k AED."
    #entities = [(11, 25, 'NAME'), (31, 38, 'COMPANY'), (68, 80, 'PHONE'), (102, 117, 'BUDGET')]
    #biluo_tags = offsets_to_biluo_tags(nlp.make_doc(text), entities)

    #print(text)
    #print(biluo_tags)
    text = example["text"]
    entities = example["entities"]
    entity_positions = [(ent["start"], ent["end"], ent["label"]) for ent in entities]
    biluo_tags = offsets_to_biluo_tags(nlp.make_doc(text), entity_positions)
    print(f"Text: {text}")
    print(f"Entities: {entity_positions}")
    print(f"BILOU Tags: {biluo_tags}")
    print("\n-------------------\n")
    if "-" in biluo_tags:
        print(f"Skipping example with misaligned entities: {text}")
        continue
    print(text)
    print(biluo_tags)
    print("Entities:", entity_positions)
    print()
    ent_list = []
    for entity in entities:
        start = entity["start"]
        end = entity["end"]
        label = entity["label"]
        ent_list.append((start, end, label))
    example = Example.from_dict(nlp.make_doc(text), {"entities": ent_list})
    train_examples.append(example)

# Training loop
n_iter = 5000
for _ in range(n_iter):
    random.shuffle(train_examples)
    losses = {}
    for example in train_examples:
        # Update the NER model with the examples
        nlp.update([example], losses=losses)

# Save the NER model to disk
nlp.to_disk("astudio_email_parser")
