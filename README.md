# parse_email

Set Up a Virtual Environment (Recommended):
On the other device, it's a good practice to create a virtual environment to install the required packages. This avoids potential conflicts with other Python packages that might be installed globally.

For example, using virtualenv:

`pip install virtualenv`

`virtualenv my_env`

`source my_env/bin/activate`  # On Windows, use: my_env\Scripts\activate

Install the Requirements:
Navigate to the directory containing the requirements.txt file (using cd your_directory_path). Then run:

`pip install -r requirements.txt`

This will read the requirements.txt file and install all the listed packages with the specified versions.

For SpaCy Models:
If your requirements involve specific models for libraries like spaCy, you might need additional steps. For instance, after installing spaCy through the requirements file, you'd still need to download the en_core_web_sm model:

`python -m spacy download en_core_web_sm`

then run:

`python web_service.py`
