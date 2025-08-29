import asyncio

from src.core.config import Config
from pipeline import Pipeline

async def main():
    config = Config()
    target_dir = 'C:\\Users\\h3098\\Desktop\\Repos\\HousePrice.WebService.Community'
    run_id = '20250829T105737Z'
    appoint_entries = ['BuildAddressController.GetListByCommunityId', 'BuilderController.GetLitigationListAsync']
    lang = '中文'    
    pipeline = Pipeline(config)
    await pipeline.run(
        target_dir=target_dir,
        lang=lang,
        run_id=run_id,
        appoint_entries=appoint_entries
    )

if __name__ == "__main__":
    asyncio.run(main())
