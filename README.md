
This project was developed following a comprehensive learning session led by Ashita Batra (PhD Scholar, IIT-Guwahati) focusing on the practical implementation of APIs. 

**Core Concepts Explored:**
*   **What is an API?** An Application Programming Interface (API) is a software bridge that allows different applications to communicate and share data seamlessly.
*   **API Applications:** This project utilizes APIs for dynamic geolocation mapping and fetching real-time meteorological data.

**Key Features:**
*   **Multi Stage API integration** - The API acts as a translator (i.e., string into spatial coordinates). Afterwards, the API fetches the required metrological data. Another key implementation was no usage of API keys so we don't have to worry about hitting limit.
*   Implements robust session management using **retry and backoff logic** to handle network instability.
*   **Interactive UI with Streamlit** - This helps in turning python code into reactive web app, works as a continuous loop .
*   **Data Transformation with Pandas & Visualization** - Raw API data is usually in the JSON format. For helping in better understanding, I have used pandas to convert into tabular format. Also by visualizing 7-days or 14-days trend, allows user to spot pattern. 
