package com.heebie.itemfusion;

import java.util.Optional;
import net.minecraft.network.protocol.game.ClientboundContainerSetSlotPacket;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Container;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.ContainerLevelAccess;
import net.minecraft.world.inventory.CraftingContainer;
import net.minecraft.world.inventory.ResultContainer;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.inventory.TransientCraftingContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

public class FusionTableMenu extends AbstractContainerMenu {
    public static final int RESULT_SLOT = 0;
    private final CraftingContainer craftSlots = new TransientCraftingContainer(this, 3, 3);
    private final ResultContainer resultSlots = new ResultContainer();
    private final ContainerLevelAccess access;
    private final Player player;

    public FusionTableMenu(int containerId, Inventory playerInventory) {
        this(containerId, playerInventory, ContainerLevelAccess.NULL);
    }

    public FusionTableMenu(int containerId, Inventory playerInventory, ContainerLevelAccess access) {
        super(ModRegistry.FUSION_MENU.get(), containerId);
        this.access = access;
        this.player = playerInventory.player;
        this.addSlot(new FusionResultSlot(playerInventory.player, this.craftSlots, this.resultSlots, 0, 124, 35));

        for (int row = 0; row < 3; ++row) {
            for (int col = 0; col < 3; ++col) {
                this.addSlot(new Slot(this.craftSlots, col + row * 3, 30 + col * 18, 17 + row * 18));
            }
        }
        for (int row = 0; row < 3; ++row) {
            for (int col = 0; col < 9; ++col) {
                this.addSlot(new Slot(playerInventory, col + row * 9 + 9, 8 + col * 18, 84 + row * 18));
            }
        }
        for (int col = 0; col < 9; ++col) {
            this.addSlot(new Slot(playerInventory, col, 8 + col * 18, 142));
        }
    }

    protected static void refreshResult(AbstractContainerMenu menu, Level level, Player player,
                                        CraftingContainer craftSlots, ResultContainer resultSlots) {
        if (!level.isClientSide) {
            ServerPlayer serverPlayer = (ServerPlayer) player;
            ItemStack stack = ItemStack.EMPTY;
            Optional<FusionRecipe> optional = level.getServer().getRecipeManager()
                .getRecipeFor(ModRegistry.FUSION_RECIPE_TYPE.get(), craftSlots, level);
            if (optional.isPresent()) {
                FusionRecipe recipe = optional.get();
                if (resultSlots.setRecipeUsed(level, serverPlayer, recipe)) {
                    ItemStack assembled = recipe.assemble(craftSlots, level.registryAccess());
                    if (assembled.isItemEnabled(level.enabledFeatures())) {
                        stack = assembled;
                    }
                }
            }
            resultSlots.setItem(0, stack);
            menu.setRemoteSlot(0, stack);
            serverPlayer.connection.send(
                new ClientboundContainerSetSlotPacket(menu.containerId, menu.incrementStateId(), 0, stack));
        }
    }

    @Override
    public void slotsChanged(Container container) {
        this.access.execute((level, pos) ->
            refreshResult(this, level, this.player, this.craftSlots, this.resultSlots));
    }

    @Override
    public void removed(Player player) {
        super.removed(player);
        this.access.execute((level, pos) -> this.clearContainer(player, this.craftSlots));
    }

    @Override
    public boolean stillValid(Player player) {
        return stillValid(this.access, player, ModRegistry.FUSION_TABLE.get());
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack result = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);
        if (slot != null && slot.hasItem()) {
            ItemStack slotStack = slot.getItem();
            result = slotStack.copy();
            final ItemStack original = result;
            if (index == RESULT_SLOT) {
                this.access.execute((level, pos) -> slotStack.getItem().onCraftedBy(slotStack, level, player));
                if (!this.moveItemStackTo(slotStack, 10, 46, true)) {
                    return ItemStack.EMPTY;
                }
                if (slot instanceof FusionResultSlot fusionSlot) {
                    fusionSlot.onQuickTake(slotStack, original);
                }
            } else if (index >= 10 && index < 46) {
                if (!this.moveItemStackTo(slotStack, 1, 10, false)) {
                    if (index < 37) {
                        if (!this.moveItemStackTo(slotStack, 37, 46, false)) {
                            return ItemStack.EMPTY;
                        }
                    } else if (!this.moveItemStackTo(slotStack, 10, 37, false)) {
                        return ItemStack.EMPTY;
                    }
                }
            } else if (!this.moveItemStackTo(slotStack, 10, 46, false)) {
                return ItemStack.EMPTY;
            }

            if (slotStack.isEmpty()) {
                slot.setByPlayer(ItemStack.EMPTY);
            } else {
                slot.setChanged();
            }
            if (slotStack.getCount() == result.getCount()) {
                return ItemStack.EMPTY;
            }
            slot.onTake(player, slotStack);
            if (index == RESULT_SLOT) {
                player.drop(slotStack, false);
            }
        }
        return result;
    }

    @Override
    public boolean canTakeItemForPickAll(ItemStack stack, Slot slot) {
        return slot.container != this.resultSlots && super.canTakeItemForPickAll(stack, slot);
    }
}
