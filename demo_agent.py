from app.agent import ProductionAgent
agent = ProductionAgent()
print('=== Production Agent - Standalone Test ===')
print()
queries = [
'What is LangGraph in one sentence?',
'What is 2 + 2?',
'Explain the difference between RAG and fine-tuning in 2 sentences.',
]
for query in queries: 
    print(f'Question: {query}')
    result = agent.invoke(query)
    print(f'Response: {result["response"][:150]}...')
    print(f'Model used: {result["model_used"]}')
    print(f'Error: {result["error"]}')
    print()