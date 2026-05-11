from pathlib import Path


class MemoryLoader:

    def load_markdown_memories(self):

        memory_path = Path("memory/context")

        contents = []

        for file in memory_path.glob("*.md"):

            with open(file, "r") as f:
                contents.append(f.read())

        return "\n\n".join(contents)


memory_loader = MemoryLoader()
