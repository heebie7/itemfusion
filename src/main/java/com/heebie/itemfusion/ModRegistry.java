package com.heebie.itemfusion;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.inventory.MenuType;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.MapColor;
import net.minecraftforge.common.extensions.IForgeMenuType;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public class ModRegistry {
    public static final DeferredRegister<Block> BLOCKS =
        DeferredRegister.create(ForgeRegistries.BLOCKS, ItemFusion.MODID);
    public static final DeferredRegister<Item> ITEMS =
        DeferredRegister.create(ForgeRegistries.ITEMS, ItemFusion.MODID);
    public static final DeferredRegister<MenuType<?>> MENU_TYPES =
        DeferredRegister.create(ForgeRegistries.MENU_TYPES, ItemFusion.MODID);
    public static final DeferredRegister<RecipeType<?>> RECIPE_TYPES =
        DeferredRegister.create(ForgeRegistries.RECIPE_TYPES, ItemFusion.MODID);
    public static final DeferredRegister<RecipeSerializer<?>> RECIPE_SERIALIZERS =
        DeferredRegister.create(ForgeRegistries.RECIPE_SERIALIZERS, ItemFusion.MODID);

    public static final RegistryObject<Block> FUSION_TABLE = BLOCKS.register("fusion_table",
        () -> new FusionTableBlock(BlockBehaviour.Properties.of()
            .mapColor(MapColor.WOOD)
            .strength(2.5F)
            .sound(SoundType.WOOD)));

    public static final RegistryObject<Item> FUSION_TABLE_ITEM = ITEMS.register("fusion_table",
        () -> new BlockItem(FUSION_TABLE.get(), new Item.Properties()));

    public static final RegistryObject<Item> FUSION_CORE = ITEMS.register("fusion_core",
        () -> new Item(new Item.Properties()));

    public static final RegistryObject<MenuType<FusionTableMenu>> FUSION_MENU = MENU_TYPES.register("fusion_table",
        () -> IForgeMenuType.create((windowId, inv, data) -> new FusionTableMenu(windowId, inv)));

    public static final RegistryObject<RecipeType<FusionRecipe>> FUSION_RECIPE_TYPE = RECIPE_TYPES.register("fusion",
        () -> RecipeType.simple(new ResourceLocation(ItemFusion.MODID, "fusion")));

    public static final RegistryObject<RecipeSerializer<FusionRecipe>> FUSION_SERIALIZER =
        RECIPE_SERIALIZERS.register("fusion", FusionRecipe.Serializer::new);
}
