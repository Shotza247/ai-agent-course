Set-up a virtual Env
```
py -m venv .venv
```

Activate the Env
```
.venv\Scripts\Activate.ps1
```

Install these libraries inside the Env
```
pip install langchain langchain-huggingface transformers duckduckgo-search python-dotenv beautifulsoup4
```

Verify that we have these libraries in place
```
py -c "import langchain, transformers; print('The setup was successful')"
```

You should see: "The setup was successful" if everything worked