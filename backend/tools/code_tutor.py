"""Interactive Code Tutor — generates challenges, validates solutions, tracks progress."""
import json
import os
import random
from datetime import datetime

PROGRESS_DIR = os.path.expanduser("~/claude-ui/notes/CodeTutor")
os.makedirs(PROGRESS_DIR, exist_ok=True)

# Challenge database organized by topic and difficulty
CHALLENGES = {
    "python_basics": {
        "name": "Python Basics",
        "challenges": [
            {"id": "pb1", "difficulty": "beginner", "title": "Hello World", "description": "Write a function called `greet` that takes a name and returns 'Hello, {name}!'", "test_code": "assert greet('Alice') == 'Hello, Alice!'\nassert greet('World') == 'Hello, World!'\nprint('All tests passed!')", "hint": "Use an f-string: f'Hello, {name}!'", "language": "python"},
            {"id": "pb2", "difficulty": "beginner", "title": "Even or Odd", "description": "Write a function `is_even` that returns True if a number is even, False if odd.", "test_code": "assert is_even(2) == True\nassert is_even(3) == False\nassert is_even(0) == True\nassert is_even(-4) == True\nprint('All tests passed!')", "hint": "Use the modulo operator: number % 2 == 0", "language": "python"},
            {"id": "pb3", "difficulty": "beginner", "title": "Sum of List", "description": "Write a function `sum_list` that takes a list of numbers and returns their sum. Don't use the built-in sum().", "test_code": "assert sum_list([1, 2, 3]) == 6\nassert sum_list([]) == 0\nassert sum_list([10, -5, 3]) == 8\nprint('All tests passed!')", "hint": "Use a for loop and an accumulator variable.", "language": "python"},
            {"id": "pb4", "difficulty": "intermediate", "title": "FizzBuzz", "description": "Write a function `fizzbuzz` that takes a number n and returns a list of strings from 1 to n. For multiples of 3 use 'Fizz', for 5 use 'Buzz', for both use 'FizzBuzz', otherwise the number as string.", "test_code": "result = fizzbuzz(15)\nassert result[0] == '1'\nassert result[2] == 'Fizz'\nassert result[4] == 'Buzz'\nassert result[14] == 'FizzBuzz'\nassert len(result) == 15\nprint('All tests passed!')", "hint": "Check divisibility by 15 first (both 3 and 5), then 3, then 5.", "language": "python"},
            {"id": "pb5", "difficulty": "intermediate", "title": "Reverse String", "description": "Write a function `reverse_string` that reverses a string without using slicing [::-1] or reversed().", "test_code": "assert reverse_string('hello') == 'olleh'\nassert reverse_string('') == ''\nassert reverse_string('a') == 'a'\nassert reverse_string('racecar') == 'racecar'\nprint('All tests passed!')", "hint": "Build a new string by iterating from the end, or use a list and swap.", "language": "python"},
        ]
    },
    "oop_basics": {
        "name": "OOP Fundamentals",
        "challenges": [
            {"id": "oop1", "difficulty": "beginner", "title": "Create a Class", "description": "Create a class `Dog` with attributes `name` and `breed` set in __init__, and a method `bark` that returns '{name} says Woof!'", "test_code": "d = Dog('Rex', 'Labrador')\nassert d.name == 'Rex'\nassert d.breed == 'Labrador'\nassert d.bark() == 'Rex says Woof!'\nprint('All tests passed!')", "hint": "class Dog:\n    def __init__(self, name, breed):\n        self.name = name\n        ...", "language": "python"},
            {"id": "oop2", "difficulty": "beginner", "title": "Inheritance", "description": "Create a class `Animal` with a `name` attribute and `speak` method that returns 'Some sound'. Then create `Cat` that inherits from Animal and overrides `speak` to return '{name} says Meow!'", "test_code": "a = Animal('Generic')\nassert a.speak() == 'Some sound'\nc = Cat('Whiskers')\nassert c.speak() == 'Whiskers says Meow!'\nassert isinstance(c, Animal)\nprint('All tests passed!')", "hint": "class Cat(Animal): means Cat inherits from Animal. Override speak() in the Cat class.", "language": "python"},
            {"id": "oop3", "difficulty": "intermediate", "title": "Encapsulation", "description": "Create a `BankAccount` class with a private `_balance` attribute (starts at 0). Add methods: `deposit(amount)`, `withdraw(amount)` (returns False if insufficient funds), and `get_balance()`.", "test_code": "acc = BankAccount()\nassert acc.get_balance() == 0\nacc.deposit(100)\nassert acc.get_balance() == 100\nassert acc.withdraw(30) == True\nassert acc.get_balance() == 70\nassert acc.withdraw(200) == False\nassert acc.get_balance() == 70\nprint('All tests passed!')", "hint": "Use self._balance as a private attribute. withdraw() should check if balance >= amount before subtracting.", "language": "python"},
            {"id": "oop4", "difficulty": "intermediate", "title": "Polymorphism", "description": "Create classes `Circle` and `Rectangle`, both with an `area()` method. Circle takes `radius`, Rectangle takes `width` and `height`. Then write a function `total_area(shapes)` that returns the sum of all areas.", "test_code": "import math\nc = Circle(5)\nr = Rectangle(3, 4)\nassert abs(c.area() - 78.5398) < 0.01\nassert r.area() == 12\nassert abs(total_area([c, r]) - 90.5398) < 0.01\nprint('All tests passed!')", "hint": "Circle area = pi * r^2, Rectangle area = width * height. total_area() just loops and calls .area() on each.", "language": "python"},
            {"id": "oop5", "difficulty": "advanced", "title": "Design Pattern: Observer", "description": "Implement a simple Observer pattern. Create `EventEmitter` class with methods: `on(event, callback)` to register a listener, `emit(event, *args)` to call all listeners for that event.", "test_code": "results = []\ndef handler(msg): results.append(msg)\nem = EventEmitter()\nem.on('greet', handler)\nem.emit('greet', 'hello')\nem.emit('greet', 'world')\nassert results == ['hello', 'world']\nprint('All tests passed!')", "hint": "Store callbacks in a dict: {event_name: [list of callbacks]}. emit() loops through callbacks and calls each one.", "language": "python"},
        ]
    },
    "data_structures": {
        "name": "Data Structures",
        "challenges": [
            {"id": "ds1", "difficulty": "beginner", "title": "Stack", "description": "Implement a `Stack` class with methods: `push(item)`, `pop()` (returns None if empty), `peek()` (returns top without removing), and `is_empty()`.", "test_code": "s = Stack()\nassert s.is_empty() == True\ns.push(1)\ns.push(2)\nassert s.peek() == 2\nassert s.pop() == 2\nassert s.pop() == 1\nassert s.pop() is None\nprint('All tests passed!')", "hint": "Use a list internally. push = append, pop = pop from end, peek = look at last element.", "language": "python"},
            {"id": "ds2", "difficulty": "intermediate", "title": "Linked List", "description": "Create a `Node` class with `value` and `next`. Create a `LinkedList` class with `append(value)`, `to_list()` (returns Python list of values), and `length()`.", "test_code": "ll = LinkedList()\nll.append(1)\nll.append(2)\nll.append(3)\nassert ll.to_list() == [1, 2, 3]\nassert ll.length() == 3\nprint('All tests passed!')", "hint": "LinkedList has a `head` attribute. append() walks to the end and adds a new Node.", "language": "python"},
            {"id": "ds3", "difficulty": "advanced", "title": "Binary Search", "description": "Write a function `binary_search(arr, target)` that returns the index of target in a sorted array, or -1 if not found. Must be O(log n).", "test_code": "assert binary_search([1, 3, 5, 7, 9], 5) == 2\nassert binary_search([1, 3, 5, 7, 9], 1) == 0\nassert binary_search([1, 3, 5, 7, 9], 9) == 4\nassert binary_search([1, 3, 5, 7, 9], 4) == -1\nassert binary_search([], 1) == -1\nprint('All tests passed!')", "hint": "Use two pointers (low, high). Check the middle element. If target < mid, search left half. If target > mid, search right half.", "language": "python"},
        ]
    },
    "javascript_basics": {
        "name": "JavaScript Basics",
        "challenges": [
            {"id": "js1", "difficulty": "beginner", "title": "Arrow Functions", "description": "Write an arrow function `double` that takes a number and returns it doubled. Then write `doubleAll` that takes an array and returns a new array with all values doubled using map.", "test_code": "console.assert(double(5) === 10);\nconsole.assert(doubleAll([1,2,3]).join() === '2,4,6');\nconsole.log('All tests passed!');", "hint": "const double = (n) => n * 2; const doubleAll = (arr) => arr.map(double);", "language": "javascript"},
            {"id": "js2", "difficulty": "intermediate", "title": "Async/Await", "description": "Write an async function `fetchData` that returns a Promise that resolves to 'Hello World' after a simulated delay. Use setTimeout wrapped in a Promise.", "test_code": "fetchData().then(result => { console.assert(result === 'Hello World'); console.log('All tests passed!'); });", "hint": "Return new Promise((resolve) => setTimeout(() => resolve('Hello World'), 100));", "language": "javascript"},
        ]
    },
    "swift_basics": {
        "name": "Swift Basics",
        "challenges": [
            {"id": "sw1", "difficulty": "beginner", "title": "Optionals", "description": "Write a function `safeDivide(_ a: Int, _ b: Int) -> Int?` that returns nil if b is 0, otherwise returns a/b.", "test_code": "// Swift challenges are explained, not auto-tested\nprint('Review: safeDivide should return nil for division by zero, and the quotient otherwise.')", "hint": "Use guard or if-else to check b == 0. Return type is Int? (optional).", "language": "python"},
        ]
    }
}


def get_topics() -> list[dict]:
    """List all available topics."""
    return [{"id": k, "name": v["name"], "challenge_count": len(v["challenges"])} for k, v in CHALLENGES.items()]


def get_challenge(topic_id: str, difficulty: str = "", challenge_id: str = "") -> dict | None:
    """Get a specific or random challenge from a topic."""
    topic = CHALLENGES.get(topic_id)
    if not topic:
        return None

    challenges = topic["challenges"]
    if challenge_id:
        for c in challenges:
            if c["id"] == challenge_id:
                return c
        return None

    if difficulty:
        filtered = [c for c in challenges if c["difficulty"] == difficulty]
        if filtered:
            return random.choice(filtered)

    return random.choice(challenges)


def validate_solution(challenge_id: str, user_code: str) -> dict:
    """Run user's code against challenge test cases."""
    # Find the challenge
    challenge = None
    for topic in CHALLENGES.values():
        for c in topic["challenges"]:
            if c["id"] == challenge_id:
                challenge = c
                break

    if not challenge:
        return {"error": f"Challenge {challenge_id} not found"}

    import subprocess
    language = challenge.get("language", "python")
    full_code = user_code + "\n\n" + challenge["test_code"]

    try:
        if language == "python":
            result = subprocess.run(["python3", "-c", full_code], capture_output=True, text=True, timeout=10)
        elif language == "javascript":
            result = subprocess.run(["node", "-e", full_code], capture_output=True, text=True, timeout=10)
        else:
            return {"error": f"Unsupported language: {language}"}

        passed = result.returncode == 0 and "All tests passed" in result.stdout
        return {
            "passed": passed,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.stderr else "",
            "challenge_id": challenge_id,
            "challenge_title": challenge["title"],
        }
    except subprocess.TimeoutExpired:
        return {"passed": False, "output": "", "error": "Code timed out (10s limit)"}
    except Exception as e:
        return {"passed": False, "output": "", "error": str(e)}


def save_progress(topic: str, challenge_id: str, passed: bool) -> dict:
    """Track learning progress."""
    progress_file = os.path.join(PROGRESS_DIR, "progress.json")
    if os.path.exists(progress_file):
        with open(progress_file) as f:
            progress = json.load(f)
    else:
        progress = {"completed": [], "attempts": {}, "started": datetime.now().isoformat()}

    key = f"{topic}:{challenge_id}"
    progress["attempts"][key] = progress["attempts"].get(key, 0) + 1

    if passed and key not in progress["completed"]:
        progress["completed"].append(key)

    progress["last_activity"] = datetime.now().isoformat()

    with open(progress_file, "w") as f:
        json.dump(progress, f, indent=2)

    total_challenges = sum(len(t["challenges"]) for t in CHALLENGES.values())
    return {
        "completed": len(progress["completed"]),
        "total": total_challenges,
        "percentage": round(len(progress["completed"]) / total_challenges * 100, 1),
        "attempts": progress["attempts"].get(key, 0),
    }


def get_progress() -> dict:
    """Get current learning progress."""
    progress_file = os.path.join(PROGRESS_DIR, "progress.json")
    if not os.path.exists(progress_file):
        return {"completed": 0, "total": sum(len(t["challenges"]) for t in CHALLENGES.values()), "percentage": 0}

    with open(progress_file) as f:
        progress = json.load(f)

    total = sum(len(t["challenges"]) for t in CHALLENGES.values())
    return {
        "completed": len(progress.get("completed", [])),
        "total": total,
        "percentage": round(len(progress.get("completed", [])) / total * 100, 1),
        "completed_list": progress.get("completed", []),
        "attempts": progress.get("attempts", {}),
    }
