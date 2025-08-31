# Standard Library Imports
import os
from typing import List

# Third-Party Imports
import pandas as pd  # For handling CSV data and dataframes
from dotenv import load_dotenv
# LangChain's document object for storing content + metadata
from langchain_core.documents import Document
from langchain_astradb import AstraDBVectorStore

# Local Application Imports
from product_assistant.utils.model_loader import ModelLoader
from product_assistant.utils.config_loader import load_config


class DataIngestion:
    """
    Handles data transformation and ingestion into AstraDB vector store.

    This class:
        - Loads environment variables and validates them.
        - Reads product review data from a CSV file.
        - Transforms the reviews into LangChain Document objects.
        - Stores the documents into AstraDB vector store.
        - Provides a sample query execution for verification.
    """

    def __init__(self):
        """
        Initialize the DataIngestion pipeline by loading environment variables,
        model loader, CSV data, and configuration.
        """
        print("Initializing DataIngestion pipeline...")

        self.model_loader = ModelLoader()
        self._load_env_variables()
        self.csv_path = self._get_csv_path()
        self.product_data = self._load_csv()
        self.config = load_config()

    def _load_env_variables(self):
        """
        Load and validate required environment variables from the .env file.

        Raises:
            EnvironmentError: If one or more required environment variables are missing.
        """
        load_dotenv()

        required_vars = [
            "GOOGLE_API_KEY",
            "ASTRA_DB_API_ENDPOINT",
            "ASTRA_DB_APPLICATION_TOKEN",
            "ASTRA_DB_KEYSPACE",
        ]

        missing_vars = [var for var in required_vars if os.getenv(var) is None]
        if missing_vars:
            raise EnvironmentError(f"Missing environment variables: {missing_vars}")

        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.db_api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
        self.db_application_token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        self.db_keyspace = os.getenv("ASTRA_DB_KEYSPACE")

    def _get_csv_path(self) -> str:
        """
        Build the file path to the product reviews CSV.

        Returns:
            str: Absolute path to the CSV file.

        Raises:
            FileNotFoundError: If the file is not found in the expected location.
        """
        current_dir = os.getcwd()
        csv_path = os.path.join(current_dir, "data", "product_reviews.csv")

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found at: {csv_path}")

        return csv_path

    def _load_csv(self) -> pd.DataFrame:
        """
        Load product reviews from the CSV file into a DataFrame.

        Returns:
            pd.DataFrame: DataFrame containing product reviews.

        Raises:
            ValueError: If the CSV file does not contain required columns.
        """
        df = pd.read_csv(self.csv_path)

        expected_columns = {
            "product_id",
            "product_title",
            "rating",
            "total_reviews",
            "price",
            "top_reviews",
        }

        if not expected_columns.issubset(set(df.columns)):
            raise ValueError(f"CSV must contain columns: {expected_columns}")

        return df

    def transform_data(self) -> List[Document]:
        """
        Transform product review data into a list of LangChain Document objects.

        Returns:
            List[Document]: A list of Document objects with product metadata and reviews.
        """
        product_list = []

        for _, row in self.product_data.iterrows():
            product_entry = {
                "product_id": row["product_id"],
                "product_title": row["product_title"],
                "rating": row["rating"],
                "total_reviews": row["total_reviews"],
                "price": row["price"],
                "top_reviews": row["top_reviews"],
            }
            product_list.append(product_entry)

        documents = []
        for entry in product_list:
            metadata = {
                "product_id": entry["product_id"],
                "product_title": entry["product_title"],
                "rating": entry["rating"],
                "total_reviews": entry["total_reviews"],
                "price": entry["price"],
            }
            doc = Document(page_content=entry["top_reviews"], metadata=metadata)
            documents.append(doc)

        print(f"Transformed {len(documents)} documents.")
        return documents

    def store_in_vector_db(self, documents: List[Document]):
        """
        Store transformed documents into AstraDB vector store.

        Args:
            documents (List[Document]): List of LangChain Document objects.

        Returns:
            Tuple[AstraDBVectorStore, List[str]]:
                - The AstraDBVectorStore instance.
                - List of inserted document IDs.
        """
        collection_name = self.config["astra_db"]["collection_name"]

        vstore = AstraDBVectorStore(
            embedding=self.model_loader.load_embeddings(),
            collection_name=collection_name,
            api_endpoint=self.db_api_endpoint,
            token=self.db_application_token,
            namespace=self.db_keyspace,
        )

        inserted_ids = vstore.add_documents(documents)
        print(f"Successfully inserted {len(inserted_ids)} documents into AstraDB.")

        return vstore, inserted_ids

    def run_pipeline(self):
        """
        Execute the full data ingestion pipeline:
            1. Transform data into LangChain documents.
            2. Store documents in AstraDB vector store.
            3. Perform a sample similarity search query.
        """
        documents = self.transform_data()
        vstore, _ = self.store_in_vector_db(documents)

        query = "Can you tell me the low budget iphone?"
        results = vstore.similarity_search(query)

        print(f"\nSample search results for query: '{query}'")
        for res in results:
            print(f"Content: {res.page_content}\nMetadata: {res.metadata}\n")


if __name__ == "__main__":
    ingestion = DataIngestion()
    ingestion.run_pipeline()
