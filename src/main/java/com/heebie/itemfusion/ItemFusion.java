package com.heebie.itemfusion;

import net.minecraft.world.item.CreativeModeTabs;
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;

@Mod(ItemFusion.MODID)
public class ItemFusion {
    public static final String MODID = "itemfusion";

    public ItemFusion() {
        IEventBus modEventBus = FMLJavaModLoadingContext.get().getModEventBus();
        ModRegistry.BLOCKS.register(modEventBus);
        ModRegistry.ITEMS.register(modEventBus);
        ModRegistry.MENU_TYPES.register(modEventBus);
        ModRegistry.RECIPE_TYPES.register(modEventBus);
        ModRegistry.RECIPE_SERIALIZERS.register(modEventBus);
        modEventBus.addListener(this::addCreative);
    }

    private void addCreative(BuildCreativeModeTabContentsEvent event) {
        if (event.getTabKey() == CreativeModeTabs.FUNCTIONAL_BLOCKS) {
            event.accept(ModRegistry.FUSION_TABLE_ITEM);
        }
        if (event.getTabKey() == CreativeModeTabs.INGREDIENTS) {
            event.accept(ModRegistry.FUSION_CORE);
        }
    }
}
