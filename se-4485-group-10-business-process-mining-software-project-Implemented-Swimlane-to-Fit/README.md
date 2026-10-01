# se-4485-group-10-business-process-mining-software-project

## How to run for development

The app is composed of two parts:
- FastAPI Python Backend for performing process mining
- Next.js Frontend

### FastAPI Python Backend
1. Make sure you have Python installed, my computer is 3.17.7, but I think any newish version will probably be fine
2. Within a command prompt, navigate to the `server` folder of the repository
3. Create a virtual environment:

On windows:
```
> py -3 -m venv .venv
> .venv\Scripts\activate
```

On mac/linux:
```
$ python3 -m venv .venv
$ . .venv/bin/activate
```

Note: doing py -3 or python3 might not be needed depending on how you installed Python.

4. The virtual environment should be activated, you'll know because you'll see `(.venv)` in the command prompt.
5. Run `pip install -r requirements.txt` to install the Python packages needed to run the server
6. Run `fastapi dev` to run the server

### Next.js frontend
1. Navigate to the `client` folder in the command prompt
2. Run `npm install`
3. Run `npm run dev` to start the frontend.

Note: right now the server api address is hardcoded, but in the future it might be moved to a .env file.

