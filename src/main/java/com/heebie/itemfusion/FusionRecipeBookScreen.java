package com.heebie.itemfusion;

import java.util.List;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;

/**
 * Ingredient index: every item used in a fusion recipe, sorted by how often it
 * is used. Shows the item and its use count, never which recipes use it.
 */
public class FusionRecipeBookScreen extends Screen {
    private static final ResourceLocation BACKGROUND =
        new ResourceLocation(ItemFusion.MODID, "textures/gui/recipe_book.png");
    private static final int WIDTH = 176;
    private static final int HEIGHT = 166;
    private static final int COLS = 8;
    private static final int ROWS = 6;
    private static final int PER_PAGE = COLS * ROWS;
    private static final int GRID_X = 8;
    private static final int GRID_Y = 24;
    private static final int CELL = 20;

    private final Screen parent;
    private List<IngredientStats.Entry> entries = List.of();
    private int page;
    private int left;
    private int top;
    private Button prev;
    private Button next;

    public FusionRecipeBookScreen(Screen parent) {
        super(Component.translatable("gui.itemfusion.recipe_book"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        this.entries = IngredientStats.get();
        this.left = (this.width - WIDTH) / 2;
        this.top = (this.height - HEIGHT) / 2;
        this.prev = Button.builder(Component.literal("<"), b -> turn(-1))
            .bounds(this.left + 8, this.top + HEIGHT - 24, 20, 20).build();
        this.next = Button.builder(Component.literal(">"), b -> turn(1))
            .bounds(this.left + WIDTH - 28, this.top + HEIGHT - 24, 20, 20).build();
        this.addRenderableWidget(this.prev);
        this.addRenderableWidget(this.next);
        updateButtons();
    }

    private int pageCount() {
        return Math.max(1, (this.entries.size() + PER_PAGE - 1) / PER_PAGE);
    }

    private void turn(int delta) {
        this.page = Math.floorMod(this.page + delta, pageCount());
        updateButtons();
    }

    private void updateButtons() {
        boolean many = pageCount() > 1;
        this.prev.active = many;
        this.next.active = many;
    }

    @Override
    public void render(GuiGraphics g, int mouseX, int mouseY, float partialTick) {
        this.renderBackground(g);
        g.blit(BACKGROUND, this.left, this.top, 0, 0, WIDTH, HEIGHT);

        g.drawString(this.font, this.title, this.left + 8, this.top + 8, 0x404040, false);
        Component pages = Component.translatable("gui.itemfusion.page", this.page + 1, pageCount());
        g.drawString(this.font, pages, this.left + WIDTH - 8 - this.font.width(pages),
            this.top + HEIGHT - 18, 0x404040, false);

        int start = this.page * PER_PAGE;
        int end = Math.min(start + PER_PAGE, this.entries.size());
        ItemStack hovered = ItemStack.EMPTY;
        int hoveredUses = 0;
        for (int i = start; i < end; ++i) {
            IngredientStats.Entry entry = this.entries.get(i);
            int idx = i - start;
            int x = this.left + GRID_X + (idx % COLS) * CELL;
            int y = this.top + GRID_Y + (idx / COLS) * CELL;
            g.renderItem(entry.stack(), x, y);
            String uses = String.valueOf(entry.uses());
            g.pose().pushPose();
            g.pose().translate(0, 0, 200);
            g.drawString(this.font, uses, x + 17 - this.font.width(uses), y + 9, 0xFFFFFF, true);
            g.pose().popPose();
            if (mouseX >= x && mouseX < x + 16 && mouseY >= y && mouseY < y + 16) {
                hovered = entry.stack();
                hoveredUses = entry.uses();
            }
        }

        super.render(g, mouseX, mouseY, partialTick);

        if (!hovered.isEmpty()) {
            var lines = new java.util.ArrayList<>(getTooltipFromItem(this.minecraft, hovered));
            lines.add(Component.translatable("gui.itemfusion.used_in", hoveredUses)
                .withStyle(ChatFormatting.GRAY));
            g.renderComponentTooltip(this.font, lines, mouseX, mouseY);
        }
    }

    @Override
    public boolean mouseScrolled(double mouseX, double mouseY, double delta) {
        if (delta != 0 && pageCount() > 1) {
            turn(delta > 0 ? -1 : 1);
            return true;
        }
        return super.mouseScrolled(mouseX, mouseY, delta);
    }

    @Override
    public void onClose() {
        this.minecraft.setScreen(this.parent);
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
