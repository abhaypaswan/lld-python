"""What each design pattern is for, in the terms this repository uses.

These are the only hand-written strings in the patterns documentation. Which
problems use which pattern comes from the meta.json files, so this file changes
only when a pattern's explanation does -- not when a problem is added.

Each entry answers three questions, chosen because they are the three an
interviewer is actually probing:

    intent   -- what the pattern does, in one line
    question -- the question in the problem that makes you reach for it
    mistake  -- what goes wrong when you do not, or when you misapply it
"""

from __future__ import annotations

PATTERN_REFERENCE: dict[str, dict[str, str]] = {
    "abstract-factory": {
        "intent": "Create families of related objects whose members have to be consistent with each other.",
        "question": "Do these objects only make sense together — and would mixing two families be a bug rather than a style choice?",
        "mistake": "Reaching for it when one product would do. If the members do not have to agree, a Factory Method is the smaller answer.",
    },
    "adapter": {
        "intent": "Make an interface you do not control fit one you do.",
        "question": "Am I wrapping something I cannot change — a vendor SDK, a legacy class, a protocol?",
        "mistake": "Letting the foreign interface leak through anyway — a vendor exception type escaping, or an amount crossing the boundary in the wrong units.",
    },
    "builder": {
        "intent": "Assemble an object across several steps, validating only once it is complete.",
        "question": "Does this object need many pieces, several optional, arriving at different moments?",
        "mistake": "Using it for three arguments. A constructor is fine until half-built objects start escaping in an invalid state.",
    },
    "chain-of-responsibility": {
        "intent": "Pass a request along a chain of handlers until one of them deals with it.",
        "question": "Could any of several handlers deal with this, and should the sender not have to know which?",
        "mistake": "Copying the pattern without asking whether the chain should stop. For logging it must not; for an approval workflow it must.",
    },
    "command": {
        "intent": "Turn an operation into an object, so it can be queued, logged, or undone.",
        "question": "Do I need undo, a replayable history, or a way to defer this action?",
        "mistake": "Storing too little to invert the operation, or capturing that data at construction rather than at execution.",
    },
    "composite": {
        "intent": "Treat a single object and a group of objects through the same interface.",
        "question": "Is this a tree where a container should be usable wherever a leaf is?",
        "mistake": "Two typed child lists instead of one. Every traversal then gets written twice, and the copies drift.",
    },
    "decorator": {
        "intent": "Add behaviour around an object without changing it, by wrapping it in something of the same type.",
        "question": "Does this behaviour apply to several implementations, and should it compose with other such behaviour?",
        "mistake": "Forgetting that stacking order changes the result, and not deciding deliberately which order you want.",
    },
    "facade": {
        "intent": "Offer one simple entry point onto a subsystem that has several parts.",
        "question": "Does a caller who wants one common thing have to know about four objects to get it?",
        "mistake": "Turning it into a god object. A facade delegates; it does not accumulate the logic itself.",
    },
    "factory-method": {
        "intent": "Decide which concrete class to create in one place, so callers never name it.",
        "question": "Is the choice of implementation a decision I want made once rather than at every call site?",
        "mistake": "A factory that is only ever called with one argument — that is a constructor with extra steps.",
    },
    "iterator": {
        "intent": "Walk a collection without exposing how it is stored.",
        "question": "Should callers be able to traverse this without knowing it is a dict, a tree, or a generator?",
        "mistake": "Materialising the whole collection when a generator would let the caller stop early.",
    },
    "mediator": {
        "intent": "Route interaction between many objects through one coordinator, so they do not reference each other.",
        "question": "Would every participant otherwise hold a reference to every other, and who enforces the rules between two of them?",
        "mistake": "Confusing it with Observer. A mediator has routing logic; a subject just notifies.",
    },
    "memento": {
        "intent": "Capture an object's state so it can be restored later, without exposing its internals.",
        "question": "Do I need to put something back exactly as it was, and is the state small enough to copy?",
        "mistake": "Snapshotting something large on every change, and handing out a mutable snapshot that can be edited after the fact.",
    },
    "observer": {
        "intent": "Let interested parties subscribe to events without the source knowing who they are.",
        "question": "Should adding a new listener be registration rather than a code change at the source?",
        "mistake": "Using it where a mediator is needed — as soon as the source starts deciding who gets what, it is no longer an observer.",
    },
    "proxy": {
        "intent": "Stand in for another object with the same interface, controlling access to it.",
        "question": "Do I need caching, lazy loading, access control or logging without the caller noticing?",
        "mistake": "Caching reads and forgetting to invalidate on write, which is worse than no proxy because it is confidently wrong.",
    },
    "repository": {
        "intent": "Hide where data lives behind a collection-shaped interface.",
        "question": "Should the rest of the system care whether this comes from memory, a database, or an API?",
        "mistake": "Letting query details leak through the interface, so swapping the backing store is no longer possible.",
    },
    "singleton": {
        "intent": "Guarantee exactly one instance of something genuinely global.",
        "question": "Would two of these be an actual bug, not just wasteful?",
        "mistake": "Using it as a global variable. It is almost always the wrong answer, and it always costs testability — provide a reset.",
    },
    "state": {
        "intent": "Put behaviour in an object representing the current state, so transitions replace conditionals.",
        "question": "Does the same method need to do something different — or be refused — depending on a mode?",
        "mistake": "Keeping the state as a flag checked at the top of every method, so adding a state means revisiting all of them.",
    },
    "strategy": {
        "intent": "Make an algorithm swappable behind a common interface.",
        "question": "Is there more than one reasonable way to do this, chosen by configuration rather than by the code?",
        "mistake": "An if/else re-evaluated on every call. Real Strategy is chosen once and injected.",
    },
    "template-method": {
        "intent": "Fix the shape of an algorithm in a base class and let subclasses fill in the steps.",
        "question": "Do several implementations share a skeleton and differ only in a few steps?",
        "mistake": "Reaching for inheritance when the variation is data, not behaviour — if the subclasses differ only in the values they set, those are constructor arguments.",
    },
    "visitor": {
        "intent": "Add operations over a structure without putting them on the structure's classes.",
        "question": "Do operations keep arriving while the set of node types stays fixed?",
        "mistake": "Using it where new node types are the common change — then every visitor has to grow a method, and you have made the expensive case the frequent one.",
    },
}
