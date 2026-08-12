package com.heebie.itemfusion;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Ingredient;

/**
 * How often each item is used as a fusion ingredient, most-used first.
 * Recipes are synced to the client, so this is computed client-side on open.
 */
public class IngredientStats {
    public record Entry(ItemStack stack, int uses) {}

    private static List<Entry> cache;
    private static int cachedRecipeCount = -1;

    public static List<Entry> get() {
        var level = Minecraft.getInstance().level;
        if (level == null) {
            return List.of();
        }
        var recipes = level.getRecipeManager().getAllRecipesFor(ModRegistry.FUSION_RECIPE_TYPE.get());
        if (cache != null && cachedRecipeCount == recipes.size()) {
            return cache;
        }

        Map<Item, Integer> counts = new LinkedHashMap<>();
        for (var recipe : recipes) {
            for (Ingredient ingredient : recipe.getIngredients()) {
                for (ItemStack stack : ingredient.getItems()) {
                    if (!stack.isEmpty()) {
                        counts.merge(stack.getItem(), 1, Integer::sum);
                    }
                }
            }
        }

        List<Entry> list = new ArrayList<>(counts.size());
        counts.forEach((item, uses) -> list.add(new Entry(new ItemStack(item), uses)));
        list.sort(Comparator.<Entry>comparingInt(e -> -e.uses())
            .thenComparing(e -> e.stack().getHoverName().getString()));

        cache = List.copyOf(list);
        cachedRecipeCount = recipes.size();
        return cache;
    }

    public static void invalidate() {
        cache = null;
        cachedRecipeCount = -1;
    }
}
