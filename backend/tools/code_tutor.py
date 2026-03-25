"""Interactive Code Tutor — challenges, validation, progress tracking, and dynamic generation."""
import json
import os
import random
import subprocess
from datetime import datetime

PROGRESS_DIR = os.path.expanduser("~/claude-ui/notes/CodeTutor")
os.makedirs(PROGRESS_DIR, exist_ok=True)

# ── Challenge Database ──────────────────────────────────────────────────────

CHALLENGES = {
    "python_basics": {
        "name": "Python Basics",
        "challenges": [
            {"id": "pb1", "difficulty": "beginner", "title": "Hello World", "description": "Write a function `greet(name)` that returns 'Hello, {name}!'", "test_code": "assert greet('Alice') == 'Hello, Alice!'\nassert greet('World') == 'Hello, World!'\nprint('All tests passed!')", "hint": "Use an f-string: f'Hello, {name}!'", "language": "python"},
            {"id": "pb2", "difficulty": "beginner", "title": "Even or Odd", "description": "Write a function `is_even(n)` that returns True if n is even, False if odd.", "test_code": "assert is_even(2) == True\nassert is_even(3) == False\nassert is_even(0) == True\nassert is_even(-4) == True\nprint('All tests passed!')", "hint": "Use modulo: n % 2 == 0", "language": "python"},
            {"id": "pb3", "difficulty": "beginner", "title": "Sum of List", "description": "Write `sum_list(nums)` that returns the sum without using built-in sum().", "test_code": "assert sum_list([1, 2, 3]) == 6\nassert sum_list([]) == 0\nassert sum_list([10, -5, 3]) == 8\nprint('All tests passed!')", "hint": "Use a for loop with an accumulator.", "language": "python"},
            {"id": "pb4", "difficulty": "beginner", "title": "Max of List", "description": "Write `find_max(nums)` that returns the largest number. Don't use max(). Return None for empty list.", "test_code": "assert find_max([3, 1, 4, 1, 5]) == 5\nassert find_max([-1, -5, -2]) == -1\nassert find_max([42]) == 42\nassert find_max([]) is None\nprint('All tests passed!')", "hint": "Track the largest seen so far in a variable.", "language": "python"},
            {"id": "pb5", "difficulty": "beginner", "title": "Count Vowels", "description": "Write `count_vowels(s)` that returns the number of vowels (a,e,i,o,u) in a string. Case insensitive.", "test_code": "assert count_vowels('hello') == 2\nassert count_vowels('AEIOU') == 5\nassert count_vowels('xyz') == 0\nassert count_vowels('') == 0\nprint('All tests passed!')", "hint": "Convert to lowercase, check if each char is in 'aeiou'.", "language": "python"},
            {"id": "pb6", "difficulty": "intermediate", "title": "FizzBuzz", "description": "Write `fizzbuzz(n)` returning a list of strings 1 to n. Multiples of 3='Fizz', 5='Buzz', both='FizzBuzz', else the number as string.", "test_code": "r = fizzbuzz(15)\nassert r[0] == '1'\nassert r[2] == 'Fizz'\nassert r[4] == 'Buzz'\nassert r[14] == 'FizzBuzz'\nassert len(r) == 15\nprint('All tests passed!')", "hint": "Check 15 first (both), then 3, then 5.", "language": "python"},
            {"id": "pb7", "difficulty": "intermediate", "title": "Reverse String", "description": "Write `reverse_string(s)` without using [::-1] or reversed().", "test_code": "assert reverse_string('hello') == 'olleh'\nassert reverse_string('') == ''\nassert reverse_string('a') == 'a'\nprint('All tests passed!')", "hint": "Build a new string by looping backwards.", "language": "python"},
            {"id": "pb8", "difficulty": "intermediate", "title": "Palindrome Check", "description": "Write `is_palindrome(s)` that returns True if the string reads the same forwards and backwards. Ignore case and spaces.", "test_code": "assert is_palindrome('racecar') == True\nassert is_palindrome('Race Car') == True\nassert is_palindrome('hello') == False\nassert is_palindrome('A man a plan a canal Panama') == True\nprint('All tests passed!')", "hint": "Clean the string first: remove spaces, lowercase. Then compare to its reverse.", "language": "python"},
            {"id": "pb9", "difficulty": "intermediate", "title": "Flatten List", "description": "Write `flatten(lst)` that flattens a nested list. E.g. [1, [2, [3]], 4] -> [1, 2, 3, 4].", "test_code": "assert flatten([1, [2, [3]], 4]) == [1, 2, 3, 4]\nassert flatten([]) == []\nassert flatten([[1, 2], [3, [4, 5]]]) == [1, 2, 3, 4, 5]\nprint('All tests passed!')", "hint": "Use recursion: if an element is a list, flatten it recursively.", "language": "python"},
            {"id": "pb10", "difficulty": "intermediate", "title": "Word Frequency", "description": "Write `word_count(text)` that returns a dict of word frequencies. Lowercase all words.", "test_code": "assert word_count('the cat sat on the mat') == {'the': 2, 'cat': 1, 'sat': 1, 'on': 1, 'mat': 1}\nassert word_count('') == {}\nassert word_count('hello hello hello') == {'hello': 3}\nprint('All tests passed!')", "hint": "Split by spaces, use a dict to count.", "language": "python"},
            {"id": "pb11", "difficulty": "advanced", "title": "Matrix Transpose", "description": "Write `transpose(matrix)` that transposes a 2D list. Rows become columns.", "test_code": "assert transpose([[1,2,3],[4,5,6]]) == [[1,4],[2,5],[3,6]]\nassert transpose([[1]]) == [[1]]\nassert transpose([[1,2],[3,4],[5,6]]) == [[1,3,5],[2,4,6]]\nprint('All tests passed!')", "hint": "New matrix has len(matrix[0]) rows and len(matrix) columns.", "language": "python"},
            {"id": "pb12", "difficulty": "advanced", "title": "Group Anagrams", "description": "Write `group_anagrams(words)` that groups words that are anagrams of each other. Return a list of lists.", "test_code": "result = group_anagrams(['eat','tea','tan','ate','nat','bat'])\nresult = [sorted(g) for g in result]\nresult.sort()\nassert result == [['ate', 'eat', 'tea'], ['bat'], ['nat', 'tan']]\nprint('All tests passed!')", "hint": "Sort each word's letters as a key: ''.join(sorted(word)). Group by that key.", "language": "python"},
        ]
    },
    "oop_basics": {
        "name": "OOP Fundamentals",
        "challenges": [
            {"id": "oop1", "difficulty": "beginner", "title": "Create a Class", "description": "Create class `Dog` with `name` and `breed` in __init__, and `bark()` returning '{name} says Woof!'", "test_code": "d = Dog('Rex', 'Lab')\nassert d.name == 'Rex'\nassert d.breed == 'Lab'\nassert d.bark() == 'Rex says Woof!'\nprint('All tests passed!')", "hint": "def __init__(self, name, breed): self.name = name ...", "language": "python"},
            {"id": "oop2", "difficulty": "beginner", "title": "Inheritance", "description": "Create `Animal` with `name` and `speak()` returning 'Some sound'. Create `Cat(Animal)` overriding `speak()` to return '{name} says Meow!'", "test_code": "a = Animal('Generic')\nassert a.speak() == 'Some sound'\nc = Cat('Whiskers')\nassert c.speak() == 'Whiskers says Meow!'\nassert isinstance(c, Animal)\nprint('All tests passed!')", "hint": "class Cat(Animal): inherits from Animal. Override speak().", "language": "python"},
            {"id": "oop3", "difficulty": "beginner", "title": "String Representation", "description": "Create class `Point` with x, y coordinates. Implement `__str__` returning '(x, y)' and `__repr__` returning 'Point(x, y)'.", "test_code": "p = Point(3, 4)\nassert str(p) == '(3, 4)'\nassert repr(p) == 'Point(3, 4)'\nprint('All tests passed!')", "hint": "__str__ is for display, __repr__ is for debugging/recreating the object.", "language": "python"},
            {"id": "oop4", "difficulty": "intermediate", "title": "Encapsulation", "description": "Create `BankAccount` with private `_balance` (starts at 0). Methods: `deposit(amount)`, `withdraw(amount)` (returns False if insufficient), `get_balance()`.", "test_code": "acc = BankAccount()\nassert acc.get_balance() == 0\nacc.deposit(100)\nassert acc.get_balance() == 100\nassert acc.withdraw(30) == True\nassert acc.get_balance() == 70\nassert acc.withdraw(200) == False\nassert acc.get_balance() == 70\nprint('All tests passed!')", "hint": "withdraw() checks if balance >= amount before subtracting.", "language": "python"},
            {"id": "oop5", "difficulty": "intermediate", "title": "Polymorphism", "description": "Create `Circle(radius)` and `Rectangle(width, height)`, both with `area()`. Write `total_area(shapes)` summing all areas.", "test_code": "import math\nc = Circle(5)\nr = Rectangle(3, 4)\nassert abs(c.area() - 78.5398) < 0.01\nassert r.area() == 12\nassert abs(total_area([c, r]) - 90.5398) < 0.01\nprint('All tests passed!')", "hint": "Circle: pi*r^2. Rectangle: w*h. total_area loops and sums .area().", "language": "python"},
            {"id": "oop6", "difficulty": "intermediate", "title": "Class Methods", "description": "Create `Temperature` with `celsius` attribute. Add `@classmethod from_fahrenheit(cls, f)` that creates Temperature from F. Add `to_fahrenheit()` method.", "test_code": "t1 = Temperature(100)\nassert t1.to_fahrenheit() == 212\nt2 = Temperature.from_fahrenheit(32)\nassert t2.celsius == 0\nprint('All tests passed!')", "hint": "F to C: (f - 32) * 5/9. C to F: c * 9/5 + 32.", "language": "python"},
            {"id": "oop7", "difficulty": "intermediate", "title": "Operator Overloading", "description": "Create `Vector` class with x, y. Implement __add__ (vector addition), __eq__ (comparison), and __abs__ (magnitude).", "test_code": "import math\nv1 = Vector(1, 2)\nv2 = Vector(3, 4)\nv3 = v1 + v2\nassert v3 == Vector(4, 6)\nassert abs(abs(Vector(3, 4)) - 5.0) < 0.001\nprint('All tests passed!')", "hint": "__add__ returns Vector(self.x+other.x, self.y+other.y). __abs__ returns sqrt(x^2+y^2).", "language": "python"},
            {"id": "oop8", "difficulty": "advanced", "title": "Iterator Protocol", "description": "Create `Range` class that works like range(). Implement __iter__ and __next__. Range(start, stop) iterates from start to stop-1.", "test_code": "r = Range(1, 5)\nresult = [x for x in r]\nassert result == [1, 2, 3, 4]\nassert list(Range(0, 3)) == [0, 1, 2]\nprint('All tests passed!')", "hint": "__iter__ returns self. __next__ returns current value and increments, raises StopIteration when done.", "language": "python"},
            {"id": "oop9", "difficulty": "advanced", "title": "Decorator Pattern", "description": "Create a decorator `@timer` that prints how long a function takes to run and returns the result normally.", "test_code": "import time\n@timer\ndef slow():\n    time.sleep(0.1)\n    return 42\nresult = slow()\nassert result == 42\nprint('All tests passed!')", "hint": "def timer(func): def wrapper(*args, **kwargs): ... return wrapper", "language": "python"},
            {"id": "oop10", "difficulty": "advanced", "title": "Observer Pattern", "description": "Create `EventEmitter` with `on(event, callback)` and `emit(event, *args)` to call all registered listeners.", "test_code": "results = []\ndef handler(msg): results.append(msg)\nem = EventEmitter()\nem.on('greet', handler)\nem.emit('greet', 'hello')\nem.emit('greet', 'world')\nassert results == ['hello', 'world']\nprint('All tests passed!')", "hint": "Dict of {event: [callbacks]}. emit loops through and calls each.", "language": "python"},
        ]
    },
    "data_structures": {
        "name": "Data Structures & Algorithms",
        "challenges": [
            {"id": "ds1", "difficulty": "beginner", "title": "Stack", "description": "Implement `Stack` with push(item), pop() (None if empty), peek(), is_empty().", "test_code": "s = Stack()\nassert s.is_empty() == True\ns.push(1)\ns.push(2)\nassert s.peek() == 2\nassert s.pop() == 2\nassert s.pop() == 1\nassert s.pop() is None\nprint('All tests passed!')", "hint": "Use a list. push=append, pop=pop from end.", "language": "python"},
            {"id": "ds2", "difficulty": "beginner", "title": "Queue", "description": "Implement `Queue` with enqueue(item), dequeue() (None if empty), peek(), is_empty().", "test_code": "q = Queue()\nassert q.is_empty() == True\nq.enqueue(1)\nq.enqueue(2)\nassert q.peek() == 1\nassert q.dequeue() == 1\nassert q.dequeue() == 2\nassert q.dequeue() is None\nprint('All tests passed!')", "hint": "Use a list. enqueue=append, dequeue=pop(0). FIFO order.", "language": "python"},
            {"id": "ds3", "difficulty": "intermediate", "title": "Linked List", "description": "Create `Node(value, next)` and `LinkedList` with append(value), to_list(), length().", "test_code": "ll = LinkedList()\nll.append(1)\nll.append(2)\nll.append(3)\nassert ll.to_list() == [1, 2, 3]\nassert ll.length() == 3\nprint('All tests passed!')", "hint": "head attribute. append walks to end, adds new Node.", "language": "python"},
            {"id": "ds4", "difficulty": "intermediate", "title": "Hash Map", "description": "Implement a simple `HashMap` with put(key, value), get(key) (returns None if missing), contains(key), keys().", "test_code": "m = HashMap()\nm.put('a', 1)\nm.put('b', 2)\nassert m.get('a') == 1\nassert m.get('c') is None\nassert m.contains('b') == True\nassert sorted(m.keys()) == ['a', 'b']\nm.put('a', 99)\nassert m.get('a') == 99\nprint('All tests passed!')", "hint": "Use a list of buckets. Hash the key to find the bucket index.", "language": "python"},
            {"id": "ds5", "difficulty": "intermediate", "title": "Binary Search", "description": "Write `binary_search(arr, target)` returning index or -1. O(log n).", "test_code": "assert binary_search([1,3,5,7,9], 5) == 2\nassert binary_search([1,3,5,7,9], 1) == 0\nassert binary_search([1,3,5,7,9], 9) == 4\nassert binary_search([1,3,5,7,9], 4) == -1\nassert binary_search([], 1) == -1\nprint('All tests passed!')", "hint": "Two pointers (low, high). Check mid. Search left or right half.", "language": "python"},
            {"id": "ds6", "difficulty": "intermediate", "title": "Bubble Sort", "description": "Write `bubble_sort(arr)` that sorts a list in place and returns it.", "test_code": "assert bubble_sort([3,1,4,1,5]) == [1,1,3,4,5]\nassert bubble_sort([]) == []\nassert bubble_sort([1]) == [1]\nassert bubble_sort([5,4,3,2,1]) == [1,2,3,4,5]\nprint('All tests passed!')", "hint": "Nested loops. Compare adjacent elements, swap if out of order. Repeat until no swaps.", "language": "python"},
            {"id": "ds7", "difficulty": "advanced", "title": "Binary Search Tree", "description": "Create `BST` with insert(value) and search(value) returning True/False, and in_order() returning sorted list.", "test_code": "t = BST()\nfor v in [5,3,7,1,4]:\n    t.insert(v)\nassert t.search(3) == True\nassert t.search(6) == False\nassert t.in_order() == [1,3,4,5,7]\nprint('All tests passed!')", "hint": "Each node has value, left, right. Insert: go left if smaller, right if bigger.", "language": "python"},
            {"id": "ds8", "difficulty": "advanced", "title": "Merge Sort", "description": "Write `merge_sort(arr)` that returns a new sorted list using merge sort algorithm.", "test_code": "assert merge_sort([3,1,4,1,5,9,2,6]) == [1,1,2,3,4,5,6,9]\nassert merge_sort([]) == []\nassert merge_sort([1]) == [1]\nprint('All tests passed!')", "hint": "Split in half, recursively sort each half, merge the two sorted halves.", "language": "python"},
            {"id": "ds9", "difficulty": "advanced", "title": "Graph BFS", "description": "Write `bfs(graph, start)` that does breadth-first traversal. Graph is a dict {node: [neighbors]}. Return list of visited nodes in BFS order.", "test_code": "g = {'A': ['B','C'], 'B': ['D'], 'C': ['D'], 'D': []}\nassert bfs(g, 'A') == ['A','B','C','D']\nprint('All tests passed!')", "hint": "Use a queue (list). Start with [start]. Pop from front, add unvisited neighbors.", "language": "python"},
        ]
    },
    "javascript_basics": {
        "name": "JavaScript",
        "challenges": [
            {"id": "js1", "difficulty": "beginner", "title": "Arrow Functions", "description": "Write `double(n)` and `doubleAll(arr)` using arrow functions and map.", "test_code": "console.assert(double(5) === 10);\nconsole.assert(doubleAll([1,2,3]).join() === '2,4,6');\nconsole.log('All tests passed!');", "hint": "const double = (n) => n * 2;", "language": "javascript"},
            {"id": "js2", "difficulty": "beginner", "title": "Array Filter", "description": "Write `getEvens(arr)` that returns only even numbers from an array using filter.", "test_code": "const r = getEvens([1,2,3,4,5,6]);\nconsole.assert(r.join() === '2,4,6');\nconsole.assert(getEvens([1,3,5]).length === 0);\nconsole.log('All tests passed!');", "hint": "arr.filter(n => n % 2 === 0)", "language": "javascript"},
            {"id": "js3", "difficulty": "intermediate", "title": "Destructuring", "description": "Write `getFullName(person)` that uses destructuring. Person has {first, last}. Return 'first last'.", "test_code": "console.assert(getFullName({first:'John',last:'Doe'}) === 'John Doe');\nconsole.log('All tests passed!');", "hint": "const {first, last} = person;", "language": "javascript"},
            {"id": "js4", "difficulty": "intermediate", "title": "Promise Chain", "description": "Write `fetchDouble(n)` that returns a Promise resolving to n*2 after 10ms delay.", "test_code": "fetchDouble(5).then(r => { console.assert(r === 10); console.log('All tests passed!'); });", "hint": "return new Promise(resolve => setTimeout(() => resolve(n*2), 10));", "language": "javascript"},
            {"id": "js5", "difficulty": "advanced", "title": "Debounce", "description": "Write `debounce(fn, ms)` that returns a function that delays calling fn until ms milliseconds after the last call.", "test_code": "let count = 0;\nconst inc = debounce(() => count++, 50);\ninc(); inc(); inc();\nsetTimeout(() => { console.assert(count === 1); console.log('All tests passed!'); }, 100);", "hint": "Use clearTimeout/setTimeout. Store the timer ID.", "language": "javascript"},
        ]
    },
    "swift_basics": {
        "name": "Swift Concepts",
        "challenges": [
            {"id": "sw1", "difficulty": "beginner", "title": "Optionals", "description": "Explain: Write `safeDivide(_ a: Int, _ b: Int) -> Int?` returning nil if b is 0. (Conceptual — explain your solution)", "test_code": "print('Swift challenges are conceptual. The AI will review your explanation.')", "hint": "guard b != 0 else { return nil }", "language": "python"},
            {"id": "sw2", "difficulty": "intermediate", "title": "Protocols", "description": "Explain: Create a protocol `Drawable` with a `draw()` method. Create `Circle` and `Square` conforming to it. (Conceptual)", "test_code": "print('Swift challenges are conceptual. The AI will review your explanation.')", "hint": "protocol Drawable { func draw() }. struct Circle: Drawable { func draw() { ... } }", "language": "python"},
            {"id": "sw3", "difficulty": "advanced", "title": "Closures", "description": "Explain: Write a function `makeCounter()` that returns a closure. Each call to the closure increments and returns a count. (Conceptual)", "test_code": "print('Swift challenges are conceptual. The AI will review your explanation.')", "hint": "func makeCounter() -> () -> Int { var count = 0; return { count += 1; return count } }", "language": "python"},
        ]
    },
}


# ── Core Functions ──────────────────────────────────────────────────────────

def get_topics() -> list[dict]:
    return [{"id": k, "name": v["name"], "challenge_count": len(v["challenges"])} for k, v in CHALLENGES.items()]


def get_challenge(topic_id: str, difficulty: str = "", challenge_id: str = "") -> dict | None:
    topic = CHALLENGES.get(topic_id)
    if not topic:
        return None
    challenges = topic["challenges"]
    if challenge_id:
        for c in challenges:
            if c["id"] == challenge_id:
                return c
        return None
    # Filter out completed ones first
    progress = get_progress()
    completed = progress.get("completed_list", [])
    available = [c for c in challenges if f"{topic_id}:{c['id']}" not in completed]
    if not available:
        available = challenges  # All done, recycle

    if difficulty:
        filtered = [c for c in available if c["difficulty"] == difficulty]
        if filtered:
            return random.choice(filtered)
    return random.choice(available)


def validate_solution(challenge_id: str, user_code: str) -> dict:
    challenge = None
    for topic in CHALLENGES.values():
        for c in topic["challenges"]:
            if c["id"] == challenge_id:
                challenge = c
                break
    if not challenge:
        return {"error": f"Challenge {challenge_id} not found"}

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

    total = sum(len(t["challenges"]) for t in CHALLENGES.values())
    return {
        "completed": len(progress["completed"]),
        "total": total,
        "percentage": round(len(progress["completed"]) / total * 100, 1),
    }


def get_progress() -> dict:
    progress_file = os.path.join(PROGRESS_DIR, "progress.json")
    if not os.path.exists(progress_file):
        total = sum(len(t["challenges"]) for t in CHALLENGES.values())
        return {"completed": 0, "total": total, "percentage": 0, "completed_list": [], "attempts": {}}
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


def validate_dynamic_challenge(user_code: str, test_code: str, language: str = "python") -> dict:
    """Validate code against dynamically generated test cases."""
    full_code = user_code + "\n\n" + test_code
    try:
        if language == "python":
            result = subprocess.run(["python3", "-c", full_code], capture_output=True, text=True, timeout=10)
        elif language == "javascript":
            result = subprocess.run(["node", "-e", full_code], capture_output=True, text=True, timeout=10)
        else:
            return {"error": f"Unsupported language: {language}"}

        passed = result.returncode == 0 and "passed" in result.stdout.lower()
        return {
            "passed": passed,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"passed": False, "output": "", "error": "Code timed out (10s limit)"}
    except Exception as e:
        return {"passed": False, "output": "", "error": str(e)}
