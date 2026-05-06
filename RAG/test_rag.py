

from rag_backend import RAGEngine

# CHANGE THIS PATH IF YOUR PDF IS IN ANOTHER FOLDER
PDF_PATH = r"C:\Users\asus\Downloads\correcton page_removed.pdf"
# Example:
# PDF_PATH = r"E:\SEM 6\ee\ee (2)\RAG\sample.pdf"


def main():
    print("Processing document...")
    bot = RAGEngine.from_pdfs([PDF_PATH])
    print("Ready.\n")

    while True:
        query = input("Enter your question (type exit to stop): ").strip()

        if query.lower() in {"exit", "quit"}:
            break

        if query.lower() in {"summarize", "summary"}:
            result = bot.summarize()
        elif query.lower() in {"key points", "keypoint", "points"}:
            result = bot.key_points()
        elif query.lower() in {"page info", "page information"}:
            result = bot.page_info()
        elif query.lower() in {"explain"}:
            result = bot.explain()
        else:
            result = bot.ask(query)

        print("\nAnswer:")
        print(result["answer"])

        if result.get("sources"):
            print("\nSources:")
            for i, src in enumerate(result["sources"], 1):
                snippet = src.text[:180].replace("\n", " ")
                print(f"{i}. {src.source} | Page {src.page} | Score {src.score:.3f}")
                print(f"   {snippet}...\n")


if __name__ == "__main__":
    main()

