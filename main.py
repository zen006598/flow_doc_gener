import asyncio

from src.core.config import Config
from pipeline import Pipeline


async def main():
    config = Config()
    target_dir = '/Users/chenjungwei/Downloads/TongDeApi'
    # target_dir = None
    run_id = '20250828T162446Z'
    appoint_entries = ['ItemController.GetAsync', 'ItemController.CreateAsync']
    
    orchestrator = Pipeline(config)
    await orchestrator.run_pipeline(
        target_dir=target_dir,
        run_id=run_id,
        appoint_entries=appoint_entries
    )

if __name__ == "__main__":
    asyncio.run(main())
