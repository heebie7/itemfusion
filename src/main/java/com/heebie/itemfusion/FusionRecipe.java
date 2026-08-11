package com.heebie.itemfusion;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonSyntaxException;
import net.minecraft.core.NonNullList;
import net.minecraft.core.RegistryAccess;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.GsonHelper;
import net.minecraft.world.entity.player.StackedContents;
import net.minecraft.world.inventory.CraftingContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.Level;
import net.minecraftforge.common.crafting.CraftingHelper;

/**
 * Shapeless "fusion" recipe: any placement in the 3x3 grid, exact ingredient
 * multiset. Data-driven:
 *
 * {
 *   "type": "itemfusion:fusion",
 *   "ingredients": [{"item": "minecraft:dirt"}, {"tag": "minecraft:logs"}],
 *   "result": {"item": "somemod:thing", "count": 1}
 * }
 */
public class FusionRecipe implements Recipe<CraftingContainer> {
    private final ResourceLocation id;
    private final NonNullList<Ingredient> ingredients;
    private final ItemStack result;

    public FusionRecipe(ResourceLocation id, NonNullList<Ingredient> ingredients, ItemStack result) {
        this.id = id;
        this.ingredients = ingredients;
        this.result = result;
    }

    @Override
    public boolean matches(CraftingContainer container, Level level) {
        StackedContents contents = new StackedContents();
        int count = 0;
        for (int i = 0; i < container.getContainerSize(); ++i) {
            ItemStack stack = container.getItem(i);
            if (!stack.isEmpty()) {
                ++count;
                contents.accountStack(stack, 1);
            }
        }
        return count == this.ingredients.size() && contents.canCraft(this, null);
    }

    @Override
    public ItemStack assemble(CraftingContainer container, RegistryAccess registryAccess) {
        return this.result.copy();
    }

    @Override
    public boolean canCraftInDimensions(int width, int height) {
        return width * height >= this.ingredients.size();
    }

    @Override
    public ItemStack getResultItem(RegistryAccess registryAccess) {
        return this.result;
    }

    @Override
    public NonNullList<Ingredient> getIngredients() {
        return this.ingredients;
    }

    @Override
    public ResourceLocation getId() {
        return this.id;
    }

    @Override
    public RecipeSerializer<?> getSerializer() {
        return ModRegistry.FUSION_SERIALIZER.get();
    }

    @Override
    public RecipeType<?> getType() {
        return ModRegistry.FUSION_RECIPE_TYPE.get();
    }

    public static class Serializer implements RecipeSerializer<FusionRecipe> {
        @Override
        public FusionRecipe fromJson(ResourceLocation id, JsonObject json) {
            JsonArray array = GsonHelper.getAsJsonArray(json, "ingredients");
            NonNullList<Ingredient> ingredients = NonNullList.create();
            for (int i = 0; i < array.size(); ++i) {
                Ingredient ingredient = Ingredient.fromJson(array.get(i));
                if (!ingredient.isEmpty()) {
                    ingredients.add(ingredient);
                }
            }
            if (ingredients.isEmpty()) {
                throw new JsonSyntaxException("No ingredients for fusion recipe " + id);
            }
            if (ingredients.size() > 9) {
                throw new JsonSyntaxException("Too many ingredients for fusion recipe " + id + " (max 9)");
            }
            ItemStack result = CraftingHelper.getItemStack(GsonHelper.getAsJsonObject(json, "result"), true);
            return new FusionRecipe(id, ingredients, result);
        }

        @Override
        public FusionRecipe fromNetwork(ResourceLocation id, FriendlyByteBuf buf) {
            int size = buf.readVarInt();
            NonNullList<Ingredient> ingredients = NonNullList.withSize(size, Ingredient.EMPTY);
            for (int i = 0; i < size; ++i) {
                ingredients.set(i, Ingredient.fromNetwork(buf));
            }
            ItemStack result = buf.readItem();
            return new FusionRecipe(id, ingredients, result);
        }

        @Override
        public void toNetwork(FriendlyByteBuf buf, FusionRecipe recipe) {
            buf.writeVarInt(recipe.ingredients.size());
            for (Ingredient ingredient : recipe.ingredients) {
                ingredient.toNetwork(buf);
            }
            buf.writeItem(recipe.result);
        }
    }
}
