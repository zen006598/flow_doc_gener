import asyncio

from src.core.config import Config
from pipeline import Pipeline

async def main():
    config = Config()
    target_dir = ''
    run_id = None
    appoint_entries = []
    lang = 'zh-TW'    
    pipeline = Pipeline(config)
    await pipeline.run(
        target_dir=target_dir,
        lang=lang,
        run_id=run_id,
        appoint_entries=appoint_entries
    )

if __name__ == "__main__":
    asyncio.run(main())
