package com.heebie.itemfusion;

import net.minecraft.core.NonNullList;
import net.minecraft.world.Container;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.CraftingContainer;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.common.ForgeHooks;
import net.minecraftforge.event.ForgeEventFactory;

/**
 * Copy of vanilla ResultSlot, except remaining items are resolved against our
 * recipe type. Vanilla ResultSlot is hardwired to RecipeType.CRAFTING — with a
 * custom recipe type its fallback would put the full ingredient stacks back
 * into the grid (item duplication).
 */
public class FusionResultSlot extends Slot {
    private final CraftingContainer craftSlots;
    private final Player player;
    private int removeCount;

    public FusionResultSlot(Player player, CraftingContainer craftSlots, Container resultContainer, int index, int x, int y) {
        super(resultContainer, index, x, y);
        this.player = player;
        this.craftSlots = craftSlots;
    }

    @Override
    public boolean mayPlace(ItemStack stack) {
        return false;
    }

    @Override
    public ItemStack remove(int amount) {
        if (this.hasItem()) {
            this.removeCount += Math.min(amount, this.getItem().getCount());
        }
        return super.remove(amount);
    }

    public void onQuickTake(ItemStack remaining, ItemStack original) {
        int moved = original.getCount() - remaining.getCount();
        if (moved > 0) {
            this.removeCount += moved;
        }
    }

    @Override
    protected void onSwapCraft(int amount) {
        this.removeCount += amount;
    }

    @Override
    protected void checkTakeAchievements(ItemStack stack) {
        if (this.removeCount > 0) {
            stack.onCraftedBy(this.player.level(), this.player, this.removeCount);
            ForgeEventFactory.firePlayerCraftingEvent(this.player, stack, this.craftSlots);
        }
        this.removeCount = 0;
    }

    @Override
    public void onTake(Player player, ItemStack stack) {
        this.checkTakeAchievements(stack);
        ForgeHooks.setCraftingPlayer(player);
        NonNullList<ItemStack> remaining = player.level().getRecipeManager()
            .getRemainingItemsFor(ModRegistry.FUSION_RECIPE_TYPE.get(), this.craftSlots, player.level());
        ForgeHooks.setCraftingPlayer(null);
        for (int i = 0; i < remaining.size(); ++i) {
            ItemStack inSlot = this.craftSlots.getItem(i);
            ItemStack rem = remaining.get(i);
            if (!inSlot.isEmpty()) {
                this.craftSlots.removeItem(i, 1);
                inSlot = this.craftSlots.getItem(i);
            }
            if (!rem.isEmpty()) {
                if (inSlot.isEmpty()) {
                    this.craftSlots.setItem(i, rem);
                } else if (ItemStack.isSameItemSameTags(inSlot, rem)) {
                    rem.grow(inSlot.getCount());
                    this.craftSlots.setItem(i, rem);
                } else if (!this.player.getInventory().add(rem)) {
                    this.player.drop(rem, false);
                }
            }
        }
    }
}
