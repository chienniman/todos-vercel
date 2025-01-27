from fasthtml.common import *
import redis
from tinyredis import TinyRedis

# CSS Styles
xtra_css = Style('''
:root {
    --font-size: 16px;
    --primary-color: #6200ea;
    --edit-color: blue;
    --add-color: green;
    --delete-color: red;
    --background-color: #f5f5f5;
    --text-color: #333;
}

body {
    font-family: Arial, sans-serif;
    font-size: var(--font-size);
    background-color: var(--background-color);
    color: var(--text-color);
    margin: 0;
    padding: 0;
}

.card {
    background-color: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    margin: 20px;
    padding: 20px;
}

button {
    border: none;
    border-radius: 4px;
    color: #fff;
    padding: 10px 20px;
    cursor: pointer;
    margin: 0 5px;
}

button.edit { background-color: var(--edit-color); }
button.add { background-color: var(--add-color); }
button.delete { background-color: var(--delete-color); }

button:hover {
    opacity: 0.9;
}

#todo-list li {
    width:100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #eee;
    padding: 10px 0;
}

#todo-list li:last-child {
    border-bottom: none;
}

input {
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 10px;
    font-size: var(--font-size);
}

.form-group {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

input[type="checkbox"] {
    transform: scale(1.2);
    margin-right: 10px;
}
''')

# FastHTML App Configuration
app = FastHTML(secret_key=os.getenv('SESSKEY', 's3kret'),
               hdrs=[picolink, xtra_css, SortableJS('.sortable')])
rt = app.route

# Todo Dataclass
@dataclass
class Todo:
    id: str = None
    title: str = ''
    done: bool = False
    priority: int = 0

# Initialize Redis
todos = TinyRedis(redis.from_url(os.environ['VERCEL_KV_URL']), Todo)

# Helper function to get Todo ID
def tid(id): return f'todo-{id}'

# Extend Todo class for frontend representation
@patch
def __ft__(self: Todo):
    show = AX(self.title, f'/todos/{self.id}', 'current-todo')
    edit = Button('edit', cls='edit', hx_get=f'/edit/{self.id}', target_id=tid(self.id))
    delete_btn = Button('delete', cls='delete', hx_delete=f'/todos/{self.id}',
                        target_id=tid(self.id), hx_swap="outerHTML")
    dt = ' ✅' if self.done else ''
    cts = [Div(dt), Div(show), Div(edit), Div(delete_btn),
           Hidden(id="id", value=self.id), Hidden(id="priority", value="0")]
    return Li(*cts, id=f'todo-{self.id}')

# Function to create input field
def mk_input(**kw): return Input(id="new-title", name="title", placeholder="New Todo", **kw)

# Route for homepage
@rt("/")
async def get():
    add = Form(Group(mk_input(required=True), Button("Add", cls="add")),
               hx_post="/", target_id='todo-list', hx_swap="beforeend")
    items = sorted(todos(), key=lambda o: o.priority)
    frm = Form(*items, id='todo-list', cls='sortable', hx_post="/reorder", hx_trigger="end")
    return Titled('Todo list', Card(Ul(frm), header=add, footer=Div(id='current-todo')))

# Route to reorder todos
@rt("/reorder")
def post(id: list[str]):
    items = todos()
    pos = {u: i for i, u in enumerate(id)}
    for o in items:
        o.priority = pos[o.id]
    todos.insert_all(items)
    return tuple(sorted(items, key=lambda o: o.priority))

# Route to delete todo
@rt("/todos/{id}")
async def delete(id: str):
    todos.delete(id)
    return clear('current-todo')

# Route to add a new todo
@rt("/")
async def post(todo: Todo):
    if not todo.title:
        return mk_input(hx_swap_oob='true')
    return todos.insert(todo), mk_input(hx_swap_oob='true')

# Route to edit todo
@rt("/edit/{id}")
async def get(id: str):
    res = Form(Group(Input(id="title"), Button("Save")),
               Hidden(id="id"), CheckboxX(id="done", label='Done'),
               hx_put="/", target_id=tid(id), id="edit")
    return fill_form(res, todos[id])

# Route to update todo
@rt("/")
async def put(todo: Todo): return todos.update(todo), clear('current-todo')

# Route to get todo details
@rt("/todos/{id}")
async def get(id: str):
    todo = todos[id]
    btn = Button('delete', cls='delete', hx_delete=f'/todos/{todo.id}',
                 target_id=tid(todo.id), hx_swap="outerHTML")
    return Div(Div(todo.title), btn)

# Serve the application
serve()
